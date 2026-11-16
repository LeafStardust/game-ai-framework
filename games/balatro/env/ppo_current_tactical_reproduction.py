"""Reproduce current selective tactics and attribute full-horizon divergence."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from hashlib import sha256
import json
import math
import multiprocessing
from pathlib import Path
from typing import Any, Callable

from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.episode_backend import PPOHeadlessBackend
from games.balatro.env.evaluation_diagnostics import derive_terminal_episode_metrics
from games.balatro.env.ppo_campaign import (
    CompletedPPOCampaign,
    _atomic_write,
    _canonical_bytes,
    load_completed_ppo_campaign,
    make_ppo_tactical_decision_engine,
)
from games.balatro.env.ppo_candidate_evaluation import (
    FIXED_EVIDENCE_KIND,
    PPOCandidateIdentity,
    execute_ppo_candidate_episode,
    fixed_candidate_policy_seed,
)
from games.balatro.env.ppo_candidate_trace import load_published_fixed_sources
from games.balatro.env.ppo_full_horizon_tactical_shadow import (
    PPO_FULL_HORIZON_TACTICAL_SHADOW_SCHEMA,
    _RecordingFullHorizonEngine,
    _first_blind_cleared,
    _load_first_blind_production,
    frozen_full_horizon_acceptance,
)
from games.balatro.env.ppo_later_tactical_trace import _load_diagnostics
from games.balatro.env.ppo_promotion_evaluation import FINAL_ARTIFACT_NAME
from games.balatro.env.seeded_evaluation import (
    FIXED_SEEDED_CORPUS_SHA256,
    FIXED_SEEDED_CORPUS_VERSION,
    FIXED_SEEDED_EPISODES,
    FixedSeededEpisodeSpec,
)
from games.balatro.live.hand_action_policy import SEARCH_SCHEDULE_SELECTIVE


PPO_CURRENT_TACTICAL_REPRODUCTION_SCHEMA = (
    "balatro-red-white-ppo-current-tactical-reproduction-v1"
)
CURRENT_TACTICAL_REPRODUCTION_REPORT_NAME = "current_tactical_reproduction.json"


class PPOCurrentTacticalReproductionError(ValueError):
    """Raised when current-production reproduction evidence drifts."""


def make_current_selective_tactical_reference():
    """Return the canonical production engine after validating its contract."""

    engine = make_ppo_tactical_decision_engine()
    if (
        engine.search_schedule_mode != SEARCH_SCHEDULE_SELECTIVE
        or engine.max_horizon != 8
        or engine.max_search_nodes != 5000
        or engine.exact_limit != 128
        or engine.child_exact_limit != 8
        or engine.max_search_seconds is not None
    ):
        raise PPOCurrentTacticalReproductionError(
            "current selective tactical contract drifted"
        )
    return engine


def _execute_current_episode(
    campaign: CompletedPPOCampaign,
    identity: PPOCandidateIdentity,
    spec: FixedSeededEpisodeSpec,
) -> dict[str, Any]:
    if (
        not isinstance(spec, FixedSeededEpisodeSpec)
        or FIXED_SEEDED_EPISODES[spec.episode_index] != spec
    ):
        raise PPOCurrentTacticalReproductionError(
            "current selective episode spec drifted"
        )
    recorder: _RecordingFullHorizonEngine | None = None

    def factory(_stream_index):
        nonlocal recorder
        recorder = _RecordingFullHorizonEngine(
            make_current_selective_tactical_reference()
        )
        return BalatroHeadlessEnvironment(PPOHeadlessBackend(recorder))

    evidence = execute_ppo_candidate_episode(
        campaign,
        identity,
        evidence_kind=FIXED_EVIDENCE_KIND,
        evidence_sha256=FIXED_SEEDED_CORPUS_SHA256,
        episode_index=spec.episode_index,
        game_seed=spec.game_seed,
        policy_seed=fixed_candidate_policy_seed(spec),
        environment_factory=factory,
    )
    if recorder is None or not recorder.decisions:
        raise PPOCurrentTacticalReproductionError(
            "current selective episode has no tactical decisions"
        )
    metrics = derive_terminal_episode_metrics(
        status=evidence.result.status,
        action_count=evidence.result.action_count,
        frames=evidence.frames,
    )
    timings = [float(item["elapsed_seconds"]) for item in recorder.decisions]
    return {
        "episode_index": spec.episode_index,
        "game_seed": spec.game_seed,
        "policy_seed": evidence.result.policy_seed,
        "status": evidence.result.status.value,
        "action_count": evidence.result.action_count,
        "metrics": asdict(metrics),
        "first_blind_cleared": _first_blind_cleared(evidence.frames),
        "tactical_decision_count": len(recorder.decisions),
        "tactical_elapsed_seconds": math.fsum(timings),
        "maximum_tactical_decision_seconds": max(timings),
        "decisions": recorder.decisions,
    }


_WORKER_CAMPAIGN: CompletedPPOCampaign | None = None
_WORKER_IDENTITY: PPOCandidateIdentity | None = None


def _initialize_worker(campaign_directory: str) -> None:
    global _WORKER_CAMPAIGN, _WORKER_IDENTITY
    _WORKER_CAMPAIGN = load_completed_ppo_campaign(campaign_directory)
    _WORKER_IDENTITY = PPOCandidateIdentity.from_completed_campaign(
        _WORKER_CAMPAIGN
    )


def _worker(spec: FixedSeededEpisodeSpec) -> dict[str, Any]:
    if _WORKER_CAMPAIGN is None or _WORKER_IDENTITY is None:
        raise PPOCurrentTacticalReproductionError(
            "current selective worker is uninitialized"
        )
    return _execute_current_episode(_WORKER_CAMPAIGN, _WORKER_IDENTITY, spec)


def _load_full_horizon_source(path: str | Path) -> tuple[dict[str, Any], str]:
    source = Path(path)
    try:
        raw = source.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PPOCurrentTacticalReproductionError(
            "full-horizon source is unreadable"
        ) from error
    if (
        not isinstance(value, dict)
        or _canonical_bytes(value) != raw
        or value.get("schema_version")
        != PPO_FULL_HORIZON_TACTICAL_SHADOW_SCHEMA
        or value.get("corpus_version") != FIXED_SEEDED_CORPUS_VERSION
        or value.get("corpus_sha256") != FIXED_SEEDED_CORPUS_SHA256
        or not isinstance(value.get("episodes"), list)
    ):
        raise PPOCurrentTacticalReproductionError(
            "full-horizon source provenance drifted"
        )
    expected = tuple(
        (spec.episode_index, spec.game_seed, fixed_candidate_policy_seed(spec))
        for spec in FIXED_SEEDED_EPISODES
    )
    actual = tuple(
        (
            episode.get("episode_index"),
            episode.get("game_seed"),
            episode.get("policy_seed"),
        )
        for episode in value["episodes"]
    )
    if actual != expected:
        raise PPOCurrentTacticalReproductionError(
            "full-horizon source order drifted"
        )
    return value, sha256(raw).hexdigest()


_STATE_FIELDS = (
    "ante",
    "round",
    "boss_name",
    "blind_requirement",
    "score",
    "hands_remaining",
    "discards_remaining",
)


def _state_projection(decision: dict[str, Any]) -> dict[str, Any]:
    try:
        return {field: decision[field] for field in _STATE_FIELDS}
    except (KeyError, TypeError) as error:
        raise PPOCurrentTacticalReproductionError(
            "tactical decision state projection is malformed"
        ) from error


def _decision_evidence(decision: dict[str, Any]) -> dict[str, Any]:
    try:
        return {
            "mode": decision["mode"],
            "action": decision["action"],
            "selected_plan": decision["selected_plan"],
            "search_attempts": decision["search_attempts"],
        }
    except (KeyError, TypeError) as error:
        raise PPOCurrentTacticalReproductionError(
            "tactical decision evidence is malformed"
        ) from error


def first_tactical_divergence(
    current: dict[str, Any],
    full_horizon: dict[str, Any],
) -> dict[str, Any] | None:
    """Return the earliest trace divergence without assuming terminal equality."""

    try:
        current_decisions = current["decisions"]
        full_decisions = full_horizon["decisions"]
    except (KeyError, TypeError) as error:
        raise PPOCurrentTacticalReproductionError(
            "tactical trace is malformed"
        ) from error
    if not isinstance(current_decisions, list) or not isinstance(
        full_decisions, list
    ):
        raise PPOCurrentTacticalReproductionError(
            "tactical trace decisions are malformed"
        )

    for index, (current_decision, full_decision) in enumerate(
        zip(current_decisions, full_decisions, strict=False)
    ):
        current_state = _state_projection(current_decision)
        full_state = _state_projection(full_decision)
        if current_state != full_state:
            return {
                "kind": "state_before_tactical_action",
                "decision_index": index,
                "shared_tactical_action_prefix_length": index,
                "current_state": current_state,
                "full_horizon_state": full_state,
            }
        current_evidence = _decision_evidence(current_decision)
        full_evidence = _decision_evidence(full_decision)
        if current_evidence["action"] != full_evidence["action"]:
            return {
                "kind": "tactical_action",
                "decision_index": index,
                "shared_tactical_action_prefix_length": index,
                "common_state": current_state,
                "current": current_evidence,
                "full_horizon": full_evidence,
            }

    if len(current_decisions) != len(full_decisions):
        index = min(len(current_decisions), len(full_decisions))
        return {
            "kind": "tactical_trace_length",
            "decision_index": index,
            "shared_tactical_action_prefix_length": index,
            "current_decision_count": len(current_decisions),
            "full_horizon_decision_count": len(full_decisions),
        }
    return None


def _outcome_projection(value: dict[str, Any]) -> dict[str, Any]:
    try:
        return {
            "status": value["status"],
            "action_count": value["action_count"],
            "metrics": value["metrics"],
            "first_blind_cleared": value["first_blind_cleared"],
        }
    except (KeyError, TypeError) as error:
        raise PPOCurrentTacticalReproductionError(
            "tactical outcome is malformed"
        ) from error


def build_reproduction_comparison(
    episodes: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    expected = tuple(
        (spec.episode_index, spec.game_seed, fixed_candidate_policy_seed(spec))
        for spec in FIXED_SEEDED_EPISODES
    )
    actual = tuple(
        (
            episode.get("episode_index"),
            episode.get("game_seed"),
            episode.get("policy_seed"),
        )
        for episode in episodes
    )
    if actual != expected:
        raise PPOCurrentTacticalReproductionError(
            "reproduction episodes are incomplete or out of order"
        )

    published_mismatches = []
    full_divergences = []
    acceptance_episodes = []
    for episode in episodes:
        published = _outcome_projection(episode["published"])
        current = _outcome_projection(episode["current_selective"])
        full = _outcome_projection(episode["full_horizon"])
        if current != published:
            published_mismatches.append(
                {
                    "episode_index": episode["episode_index"],
                    "game_seed": episode["game_seed"],
                    "published": published,
                    "current_selective": current,
                }
            )
        divergence = first_tactical_divergence(
            episode["current_selective"], episode["full_horizon"]
        )
        if current != full or divergence is not None:
            if divergence is None:
                divergence = {
                    "kind": "terminal_after_identical_tactical_trace",
                    "decision_index": episode["current_selective"][
                        "tactical_decision_count"
                    ],
                    "shared_tactical_action_prefix_length": episode[
                        "current_selective"
                    ]["tactical_decision_count"],
                }
            full_divergences.append(
                {
                    "episode_index": episode["episode_index"],
                    "game_seed": episode["game_seed"],
                    "current_selective_outcome": current,
                    "full_horizon_outcome": full,
                    "first_divergence": divergence,
                }
            )
        acceptance_episodes.append(
            {
                "episode_index": episode["episode_index"],
                "game_seed": episode["game_seed"],
                "policy_seed": episode["policy_seed"],
                "production": episode["current_selective"],
                "reference": episode["full_horizon"],
            }
        )

    failures = {
        "illegal_action_count": 0,
        "unsupported_mechanic_count": 0,
        "truncated_episode_count": 0,
        "incomplete_episode_count": 0,
    }
    return {
        "published_reproduction_exact": not published_mismatches,
        "published_mismatch_count": len(published_mismatches),
        "published_mismatches": published_mismatches,
        "full_horizon_divergence_count": len(full_divergences),
        "full_horizon_divergences": full_divergences,
        "full_horizon_vs_current_selective": frozen_full_horizon_acceptance(
            tuple(acceptance_episodes), failures
        ),
    }


def run_current_tactical_reproduction(
    campaign_directory: str | Path,
    promotion_directory: str | Path,
    production_first_blind_source: str | Path,
    full_horizon_source: str | Path,
    output_path: str | Path,
    *,
    maximum_workers: int,
    episode_executor: Callable | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    destination = Path(output_path)
    if destination.exists():
        raise PPOCurrentTacticalReproductionError(
            "current tactical reproduction output already exists"
        )
    if not destination.parent.is_dir():
        raise PPOCurrentTacticalReproductionError(
            "current tactical reproduction output directory is missing"
        )
    if (
        isinstance(maximum_workers, bool)
        or not isinstance(maximum_workers, int)
        or not 1 <= maximum_workers <= 8
    ):
        raise PPOCurrentTacticalReproductionError(
            "current tactical reproduction workers must be from 1 through 8"
        )
    if episode_executor is not None and not callable(episode_executor):
        raise TypeError("episode_executor must be callable")
    if progress_callback is not None and not callable(progress_callback):
        raise TypeError("progress_callback must be callable")

    campaign_path = Path(campaign_directory)
    promotion_path = Path(promotion_directory)
    campaign = load_completed_ppo_campaign(campaign_path)
    identity = PPOCandidateIdentity.from_completed_campaign(campaign)
    final, candidate_source, _ = load_published_fixed_sources(
        campaign, promotion_path
    )
    diagnostics, diagnostics_sha256 = _load_diagnostics(final, promotion_path)
    first_blind_sha256, production_first_blinds = _load_first_blind_production(
        production_first_blind_source
    )
    full_report, full_report_sha256 = _load_full_horizon_source(
        full_horizon_source
    )
    expected_links = {
        "candidate_sha256": identity.sha256,
        "campaign_checkpoint_sha256": campaign.checkpoint_sha256,
        "campaign_progress_sha256": campaign.progress_sha256,
        "campaign_final_sha256": campaign.final_sha256,
        "promotion_final_sha256": sha256(
            (promotion_path / FINAL_ARTIFACT_NAME).read_bytes()
        ).hexdigest(),
        "fixed_candidate_source_sha256": final["artifacts"][
            "fixed-candidate.json"
        ],
        "diagnostics_source_sha256": diagnostics_sha256,
        "production_first_blind_source_sha256": first_blind_sha256,
    }
    if any(full_report.get(key) != value for key, value in expected_links.items()):
        raise PPOCurrentTacticalReproductionError(
            "full-horizon source links drifted"
        )
    published_metrics = {
        int(item["episode_index"]): item["metrics"]
        for item in diagnostics["episodes"]
    }

    current_values: list[dict[str, Any]] = []

    def record(value: dict[str, Any]) -> None:
        current_values.append(value)
        if progress_callback is not None:
            progress_callback(len(current_values), len(FIXED_SEEDED_EPISODES))

    if episode_executor is None:
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=maximum_workers,
            mp_context=context,
            initializer=_initialize_worker,
            initargs=(str(campaign_path),),
        ) as executor:
            for value in executor.map(_worker, FIXED_SEEDED_EPISODES):
                record(value)
    else:
        for spec in FIXED_SEEDED_EPISODES:
            record(episode_executor(campaign, identity, spec))

    episodes = []
    for spec, published, current, full_episode in zip(
        FIXED_SEEDED_EPISODES,
        candidate_source.episodes,
        current_values,
        full_report["episodes"],
        strict=True,
    ):
        if (
            current.get("episode_index") != spec.episode_index
            or current.get("game_seed") != spec.game_seed
            or published.episode_index != spec.episode_index
            or published.game_seed != spec.game_seed
            or full_episode.get("episode_index") != spec.episode_index
            or full_episode.get("game_seed") != spec.game_seed
        ):
            raise PPOCurrentTacticalReproductionError(
                "current tactical reproduction episode order drifted"
            )
        episodes.append(
            {
                "episode_index": spec.episode_index,
                "game_seed": spec.game_seed,
                "policy_seed": current["policy_seed"],
                "published": {
                    "status": published.status.value,
                    "action_count": published.action_count,
                    "metrics": published_metrics[spec.episode_index],
                    "first_blind_cleared": production_first_blinds[
                        spec.episode_index
                    ],
                },
                "current_selective": current,
                "full_horizon": full_episode["reference"],
            }
        )
    episodes_tuple = tuple(episodes)
    comparison = build_reproduction_comparison(episodes_tuple)
    report = {
        "schema_version": PPO_CURRENT_TACTICAL_REPRODUCTION_SCHEMA,
        **expected_links,
        "full_horizon_source_sha256": full_report_sha256,
        "corpus_version": FIXED_SEEDED_CORPUS_VERSION,
        "corpus_sha256": FIXED_SEEDED_CORPUS_SHA256,
        "current_selective_config": {
            "search_schedule_mode": SEARCH_SCHEDULE_SELECTIVE,
            "max_horizon": 8,
            "max_search_nodes": 5000,
            "exact_combination_limit": 128,
            "child_exact_combination_limit": 8,
            "max_search_seconds": None,
        },
        "episodes": episodes,
        "comparison": comparison,
        "decision": (
            "published-exact"
            if comparison["published_reproduction_exact"]
            else "published-drift"
        ),
    }
    _atomic_write(destination, _canonical_bytes(report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-directory", required=True)
    parser.add_argument("--promotion-directory", required=True)
    parser.add_argument("--production-first-blind-source", required=True)
    parser.add_argument("--full-horizon-source", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--maximum-workers", type=int, default=8)
    arguments = parser.parse_args(argv)

    def progress(completed: int, total: int) -> None:
        print(
            _canonical_bytes(
                {"completed_episodes": completed, "total_episodes": total}
            ).decode("utf-8"),
            flush=True,
        )

    report = run_current_tactical_reproduction(
        arguments.campaign_directory,
        arguments.promotion_directory,
        arguments.production_first_blind_source,
        arguments.full_horizon_source,
        arguments.output_path,
        maximum_workers=arguments.maximum_workers,
        progress_callback=progress,
    )
    path = Path(arguments.output_path)
    print(
        _canonical_bytes(
            {
                "schema_version": report["schema_version"],
                "output_path": str(path),
                "report_sha256": sha256(path.read_bytes()).hexdigest(),
                "decision": report["decision"],
                "published_reproduction_exact": report["comparison"][
                    "published_reproduction_exact"
                ],
                "published_mismatch_count": report["comparison"][
                    "published_mismatch_count"
                ],
                "full_horizon_divergence_count": report["comparison"][
                    "full_horizon_divergence_count"
                ],
                "full_horizon_vs_current_selective": report["comparison"][
                    "full_horizon_vs_current_selective"
                ],
            }
        ).decode("utf-8")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
