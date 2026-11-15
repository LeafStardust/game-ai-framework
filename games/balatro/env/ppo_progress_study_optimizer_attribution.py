"""Exact read-only replay attribution for the rejected progress-reward study."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from hashlib import sha256
import itertools
import json
import math
import multiprocessing
from pathlib import Path
from typing import Any, Callable

import numpy as np

from games.balatro.env.action_encoding import (
    PUBLIC_ACTION_SCHEMA,
    action_from_index,
    legal_action_mask,
)
from games.balatro.env.ppo_campaign import (
    _atomic_write,
    _canonical_bytes,
    _collect_production_wave,
    make_ppo_training_environment,
)
from games.balatro.env.ppo_contract import PPOContractError
from games.balatro.env.ppo_model import PPOActorCritic, PPOBatch
from games.balatro.env.ppo_progress_study import (
    STUDY_JOURNAL_NAME,
    STUDY_MILESTONE_DIRECTORY,
    STUDY_MILESTONE_MANIFEST_NAME,
    PPOProgressStudyEpisodeRecord,
    load_progress_study_milestone,
)
from games.balatro.env.ppo_progress_study_behavior import (
    PPO_PROGRESS_STUDY_BEHAVIOR_SCHEMA,
    STUDY_BEHAVIOR_REPORT_NAME,
)
from games.balatro.env.ppo_progress_study_runner import initialize_progress_study


PPO_PROGRESS_STUDY_OPTIMIZER_ATTRIBUTION_SCHEMA = (
    "balatro-red-white-progress-study-optimizer-attribution-v1"
)
STUDY_OPTIMIZER_ATTRIBUTION_NAME = "optimizer_input_attribution.json"
_END_SHOP_INDEX = 0
_BUY_VOUCHER_INDEX = 4
_POLICY_PARAMETER_GROUPS = {
    "first_hidden": ("w1", "b1"),
    "second_hidden": ("w2", "b2"),
    "policy_head": ("policy_w", "policy_b"),
}


def _read_canonical(path: Path, label: str) -> tuple[object, bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PPOContractError(
            f"PPO optimizer attribution {label} is unreadable"
        ) from error
    if _canonical_bytes(value) != raw:
        raise PPOContractError(
            f"PPO optimizer attribution {label} is noncanonical"
        )
    return value, raw


def _finite_summary(values: np.ndarray) -> dict[str, float | int] | None:
    samples = np.asarray(values, dtype=np.float64)
    if samples.ndim != 1 or not np.all(np.isfinite(samples)):
        raise PPOContractError("PPO optimizer attribution samples are invalid")
    if not len(samples):
        return None
    return {
        "count": int(len(samples)),
        "minimum": float(np.min(samples)),
        "maximum": float(np.max(samples)),
        "mean": float(np.mean(samples)),
        "negative_count": int(np.count_nonzero(samples < 0.0)),
        "zero_count": int(np.count_nonzero(samples == 0.0)),
        "positive_count": int(np.count_nonzero(samples > 0.0)),
    }


def _batch_sha256(batch: PPOBatch) -> str:
    digest = sha256()
    for name in (
        "observations",
        "action_masks",
        "action_indices",
        "episode_indices",
        "decision_indices",
        "old_log_probabilities",
        "old_values",
        "advantages",
        "returns",
    ):
        value = np.ascontiguousarray(getattr(batch, name))
        digest.update(name.encode("ascii"))
        digest.update(value.dtype.str.encode("ascii"))
        digest.update(str(value.shape).encode("ascii"))
        digest.update(value.tobytes())
    return digest.hexdigest()


def summarize_optimizer_batch(
    batch: PPOBatch,
    model: PPOActorCritic,
    completed_batch_count: int,
) -> dict[str, Any]:
    """Summarize one exact pre-update batch without mutating it or the model."""

    if not isinstance(batch, PPOBatch) or not isinstance(model, PPOActorCritic):
        raise TypeError("optimizer attribution requires PPO batch and model owners")
    if (
        isinstance(completed_batch_count, bool)
        or not isinstance(completed_batch_count, int)
        or completed_batch_count < 1
    ):
        raise PPOContractError("optimizer attribution batch count is invalid")
    batch = batch.validated(expected_size=2048)
    probabilities, values, _ = model.evaluate_batch(
        batch.observations, batch.action_masks
    )
    if not np.allclose(values, batch.old_values, rtol=0.0, atol=1e-12):
        raise PPOContractError("optimizer attribution pre-update values drifted")
    rows = np.arange(len(batch.action_indices))
    selected = probabilities[rows, batch.action_indices]
    if not np.allclose(
        np.log(selected), batch.old_log_probabilities, rtol=0.0, atol=1e-12
    ):
        raise PPOContractError("optimizer attribution old probabilities drifted")

    slots = []
    for slot in PUBLIC_ACTION_SCHEMA.slots:
        selected_mask = batch.action_indices == slot.index
        legal_mask = batch.action_masks[:, slot.index]
        slots.append(
            {
                "index": slot.index,
                "alias": slot.alias,
                "params": dict(slot.params),
                "legal_count": int(np.count_nonzero(legal_mask)),
                "selected_count": int(np.count_nonzero(selected_mask)),
                "selected_advantages": _finite_summary(
                    batch.advantages[selected_mask]
                ),
                "selected_returns": _finite_summary(batch.returns[selected_mask]),
            }
        )

    implicated = (
        batch.action_masks[:, _END_SHOP_INDEX]
        & batch.action_masks[:, _BUY_VOUCHER_INDEX]
    )
    margin_terms = batch.advantages * (
        (batch.action_indices == _BUY_VOUCHER_INDEX).astype(np.float64)
        - (batch.action_indices == _END_SHOP_INDEX).astype(np.float64)
        - probabilities[:, _BUY_VOUCHER_INDEX]
        + probabilities[:, _END_SHOP_INDEX]
    )
    selected_groups = []
    for index in range(len(PUBLIC_ACTION_SCHEMA.slots)):
        group = implicated & (batch.action_indices == index)
        if np.any(group):
            selected_groups.append(
                {
                    "selected_action_index": index,
                    "selected_count": int(np.count_nonzero(group)),
                    "advantages": _finite_summary(batch.advantages[group]),
                    "returns": _finite_summary(batch.returns[group]),
                    "first_step_voucher_minus_end_policy_signal": float(
                        math.fsum(float(value) for value in margin_terms[group])
                    ),
                }
            )
    return {
        "completed_batch_count": completed_batch_count,
        "batch_sha256": _batch_sha256(batch),
        "transition_count": len(batch.action_indices),
        "episode_count": len(set(int(value) for value in batch.episode_indices)),
        "action_slots": slots,
        "implicated_shop_legal_set": {
            "required_action_indices": [_END_SHOP_INDEX, _BUY_VOUCHER_INDEX],
            "transition_count": int(np.count_nonzero(implicated)),
            "advantages": _finite_summary(batch.advantages[implicated]),
            "returns": _finite_summary(batch.returns[implicated]),
            "first_step_voucher_minus_end_policy_signal": float(
                math.fsum(float(value) for value in margin_terms[implicated])
            ),
            "selected_action_groups": selected_groups,
        },
    }


def shapley_policy_margin_attribution(
    initial: PPOActorCritic,
    candidate: PPOActorCritic,
    observation: tuple[float, ...],
    action_mask: tuple[bool, ...],
) -> dict[str, Any]:
    """Exactly partition one voucher-minus-end logit-margin change by blocks."""

    if not isinstance(initial, PPOActorCritic) or not isinstance(candidate, PPOActorCritic):
        raise TypeError("policy margin attribution requires two PPO models")
    values = np.asarray([observation], dtype=np.float64)
    masks = np.asarray([action_mask], dtype=np.bool_)
    if (
        values.shape[1:] != (initial.parameters["w1"].shape[0],)
        or masks.shape != (1, len(PUBLIC_ACTION_SCHEMA.slots))
        or not masks[0, _END_SHOP_INDEX]
        or not masks[0, _BUY_VOUCHER_INDEX]
    ):
        raise PPOContractError("policy margin attribution state is invalid")

    def margin(model: PPOActorCritic) -> float:
        probabilities, _, _ = model.evaluate_batch(values, masks)
        return float(
            math.log(probabilities[0, _BUY_VOUCHER_INDEX])
            - math.log(probabilities[0, _END_SHOP_INDEX])
        )

    cache: dict[frozenset[str], float] = {}

    def hybrid_margin(groups: frozenset[str]) -> float:
        if groups not in cache:
            model = deepcopy(initial)
            for group in groups:
                for name in _POLICY_PARAMETER_GROUPS[group]:
                    model.parameters[name] = candidate.parameters[name].copy()
            cache[groups] = margin(model)
        return cache[groups]

    contributions = {name: 0.0 for name in _POLICY_PARAMETER_GROUPS}
    names = tuple(_POLICY_PARAMETER_GROUPS)
    permutations = tuple(itertools.permutations(names))
    for ordering in permutations:
        selected: frozenset[str] = frozenset()
        prior = hybrid_margin(selected)
        for name in ordering:
            selected = selected | {name}
            current = hybrid_margin(selected)
            contributions[name] += (current - prior) / len(permutations)
            prior = current
    initial_margin = hybrid_margin(frozenset())
    candidate_margin = hybrid_margin(frozenset(names))
    delta = candidate_margin - initial_margin
    if not math.isclose(
        math.fsum(contributions.values()), delta, rel_tol=0.0, abs_tol=1e-12
    ):
        raise PPOContractError("policy margin Shapley attribution does not close")
    return {
        "initial_voucher_minus_end_logit_margin": initial_margin,
        "candidate_voucher_minus_end_logit_margin": candidate_margin,
        "margin_delta": delta,
        "shapley_margin_delta": contributions,
    }


def _implicated_evaluation_attribution(
    directory: Path,
    run,
    behavior: dict[str, Any],
) -> dict[str, Any]:
    models = {
        batch: load_progress_study_milestone(directory, run, batch).session.learner.model
        for batch in (0, 1, 2, 4, 8)
    }
    targets = []
    for comparison in behavior.get("comparisons_to_batch_0", ()):
        batch = comparison.get("completed_batch_count")
        for episode in comparison.get("episodes", ()):
            divergence = episode.get("first_greedy_divergence")
            if (
                isinstance(divergence, dict)
                and divergence.get("batch_0", {}).get("index") == _END_SHOP_INDEX
                and divergence.get("candidate", {}).get("index")
                == _BUY_VOUCHER_INDEX
            ):
                targets.append(
                    {
                        "completed_batch_count": batch,
                        "episode_index": episode["episode_index"],
                        "game_seed": episode["game_seed"],
                        "decision_index": divergence["decision_index"],
                        "observation_sha256": divergence["observation_sha256"],
                        "terminal_deltas": episode["terminal_deltas"],
                    }
                )
    required = {
        (target["game_seed"], target["decision_index"]): target["observation_sha256"]
        for target in targets
    }
    observed: dict[tuple[str, int], tuple[tuple[float, ...], tuple[bool, ...]]] = {}
    initial_model = models[0]
    environment = make_ppo_training_environment(0)
    by_seed: dict[str, list[int]] = {}
    for seed, decision_index in required:
        by_seed.setdefault(seed, []).append(decision_index)
    for seed, indices in sorted(by_seed.items()):
        environment.reset(seed=seed)
        wanted = set(indices)
        for decision_index in range(max(indices) + 1):
            observation = environment.frame.encoded_observation()
            mask = legal_action_mask(environment.legal_actions())
            if decision_index in wanted:
                digest = sha256(_canonical_bytes(list(observation.values))).hexdigest()
                if digest != required[(seed, decision_index)]:
                    raise PPOContractError(
                        "optimizer attribution implicated observation drifted"
                    )
                observed[(seed, decision_index)] = (observation.values, mask.values)
            output = initial_model.infer(observation, mask)
            allowed = tuple(index for index, legal in enumerate(mask.values) if legal)
            selected = min(
                allowed, key=lambda index: (-output.probabilities[index], index)
            )
            environment.step(action_from_index(selected))
    if set(observed) != set(required):
        raise PPOContractError("optimizer attribution implicated states are incomplete")

    episodes = []
    for target in targets:
        state = observed[(target["game_seed"], target["decision_index"])]
        margin = shapley_policy_margin_attribution(
            initial_model,
            models[target["completed_batch_count"]],
            state[0],
            state[1],
        )
        episodes.append({**target, **margin})
    summaries = []
    for batch in (1, 2, 4, 8):
        selected = [
            episode
            for episode in episodes
            if episode["completed_batch_count"] == batch
        ]
        if not selected:
            raise PPOContractError(
                "optimizer attribution implicated batch states are missing"
            )
        summaries.append(
            {
                "completed_batch_count": batch,
                "episode_count": len(selected),
                "mean_margin_delta": (
                    math.fsum(episode["margin_delta"] for episode in selected)
                    / len(selected)
                ),
                "mean_shapley_margin_delta": {
                    name: math.fsum(
                        episode["shapley_margin_delta"][name]
                        for episode in selected
                    )
                    / len(selected)
                    for name in _POLICY_PARAMETER_GROUPS
                },
            }
        )
    return {"summaries": summaries, "episodes": episodes}


def _expected_post_batch_hashes(records) -> dict[int, str]:
    values: dict[int, str] = {}
    for record in records:
        batch = record.completed_batch_count_after_commit
        if batch:
            prior = values.setdefault(batch, record.policy_parameter_sha256_after_commit)
            if prior != record.policy_parameter_sha256_after_commit:
                raise PPOContractError(
                    "optimizer attribution journal policy hash drifted"
                )
    if set(values) != set(range(1, 9)):
        raise PPOContractError("optimizer attribution journal batches are incomplete")
    return values


def run_progress_study_optimizer_attribution(
    artifact_directory: str | Path,
    output_path: str | Path,
    *,
    maximum_workers: int,
    wave_collector: Callable | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """Replay all eight frozen batches and require exact stored policy hashes."""

    if (
        isinstance(maximum_workers, bool)
        or not isinstance(maximum_workers, int)
        or not 1 <= maximum_workers <= 8
    ):
        raise PPOContractError("optimizer attribution workers must be from 1 through 8")
    if wave_collector is not None and not callable(wave_collector):
        raise TypeError("wave_collector must be callable")
    if progress_callback is not None and not callable(progress_callback):
        raise TypeError("progress_callback must be callable")
    destination = Path(output_path)
    if destination.exists():
        raise PPOContractError("optimizer attribution output already exists")
    if not destination.parent.is_dir():
        raise PPOContractError("optimizer attribution output directory is missing")

    directory = Path(artifact_directory)
    run, _ = initialize_progress_study(directory)
    initial = load_progress_study_milestone(directory, run, 0)
    final = load_progress_study_milestone(directory, run, 8)
    source_records = final.journal.records
    expected_hashes = _expected_post_batch_hashes(source_records)
    behavior, behavior_raw = _read_canonical(
        directory / STUDY_BEHAVIOR_REPORT_NAME, "behavior report"
    )
    if (
        not isinstance(behavior, dict)
        or behavior.get("schema") != PPO_PROGRESS_STUDY_BEHAVIOR_SCHEMA
        or behavior.get("training_run_sha256") != run.sha256
    ):
        raise PPOContractError("optimizer attribution behavior provenance drifted")
    evaluation_attribution = _implicated_evaluation_attribution(
        directory, run, behavior
    )

    session = initial.session
    cursor = 0
    batches: list[dict[str, Any]] = []

    def replay(collector: Callable) -> None:
        nonlocal cursor
        for batch_count in range(1, 9):
            pre_policy = session.learner.model.parameter_sha256
            captured: list[dict[str, Any]] = []

            def observe_batch(batch: PPOBatch) -> None:
                if captured:
                    raise PPOContractError(
                        "optimizer attribution captured multiple batches"
                    )
                captured.append(
                    summarize_optimizer_batch(
                        batch, session.learner.model, batch_count
                    )
                )

            def observe_episode(current_session, episode) -> None:
                nonlocal cursor
                if cursor >= len(source_records):
                    raise PPOContractError(
                        "optimizer attribution replay exceeded journal"
                    )
                actual = PPOProgressStudyEpisodeRecord.from_episode(
                    current_session, episode
                )
                if actual != source_records[cursor]:
                    raise PPOContractError(
                        "optimizer attribution replayed episode drifted"
                    )
                cursor += 1

            advance = session.advance_parallel(
                maximum_episodes=len(source_records) - cursor,
                maximum_batches=1,
                wave_collector=collector,
                on_episode_committed=observe_episode,
                on_batch_ready=observe_batch,
            )
            if (
                advance.batches_completed != 1
                or advance.completed_batch_count != batch_count
                or len(captured) != 1
                or session.learner.model.parameter_sha256
                != expected_hashes[batch_count]
            ):
                raise PPOContractError(
                    "optimizer attribution post-batch policy hash drifted"
                )
            captured[0]["pre_policy_parameter_sha256"] = pre_policy
            captured[0]["post_policy_parameter_sha256"] = expected_hashes[batch_count]
            batches.append(captured[0])
            if progress_callback is not None:
                progress_callback(batch_count, 8)

    if wave_collector is None:
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=maximum_workers, mp_context=context
        ) as executor:
            replay(
                lambda requests, training_run, model: _collect_production_wave(
                    executor, requests, training_run, model
                )
            )
    else:
        replay(wave_collector)

    if cursor != len(source_records):
        raise PPOContractError("optimizer attribution journal replay is incomplete")
    milestone_links = []
    for batch in (0, 1, 2, 4, 8):
        path = (
            directory
            / STUDY_MILESTONE_DIRECTORY
            / f"batch-{batch:03d}"
            / STUDY_MILESTONE_MANIFEST_NAME
        )
        milestone_links.append(
            {
                "completed_batch_count": batch,
                "milestone_manifest_sha256": sha256(path.read_bytes()).hexdigest(),
            }
        )
    journal_path = (
        directory
        / STUDY_MILESTONE_DIRECTORY
        / "batch-008"
        / STUDY_JOURNAL_NAME
    )
    report = {
        "schema": PPO_PROGRESS_STUDY_OPTIMIZER_ATTRIBUTION_SCHEMA,
        "training_run_sha256": run.sha256,
        "behavior_report_sha256": sha256(behavior_raw).hexdigest(),
        "final_journal_sha256": sha256(journal_path.read_bytes()).hexdigest(),
        "milestone_links": milestone_links,
        "replayed_episode_count": cursor,
        "batches": batches,
        "implicated_evaluation_states": evaluation_attribution,
    }
    _atomic_write(destination, _canonical_bytes(report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-directory", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--maximum-workers", type=int, default=8)
    arguments = parser.parse_args(argv)

    def progress(completed: int, total: int) -> None:
        print(
            _canonical_bytes(
                {"completed_batch_count": completed, "total_batch_count": total}
            ).decode("utf-8"),
            flush=True,
        )

    report = run_progress_study_optimizer_attribution(
        arguments.artifact_directory,
        arguments.output_path,
        maximum_workers=arguments.maximum_workers,
        progress_callback=progress,
    )
    path = Path(arguments.output_path)
    print(
        _canonical_bytes(
            {
                "schema": report["schema"],
                "output_path": str(path),
                "report_sha256": sha256(path.read_bytes()).hexdigest(),
            }
        ).decode("utf-8")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
