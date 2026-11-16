"""Fixed-corpus full-horizon reference for the frozen PPO tactical authority."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from hashlib import sha256
import json
import math
import multiprocessing
from pathlib import Path
from statistics import fmean
from time import perf_counter
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
from games.balatro.env.ppo_later_tactical_trace import _load_diagnostics
from games.balatro.env.ppo_promotion_evaluation import FINAL_ARTIFACT_NAME
from games.balatro.env.ppo_tactical_shadow import PPO_TACTICAL_SHADOW_SCHEMA
from games.balatro.env.seeded_evaluation import (
    FIXED_SEEDED_CORPUS_SHA256,
    FIXED_SEEDED_CORPUS_VERSION,
    FIXED_SEEDED_EPISODES,
    FixedSeededEpisodeSpec,
)
from games.balatro.live.adaptive_search import LIVE_ADAPTIVE_MAX_HORIZON
from games.balatro.live.hand_action_policy import (
    SEARCH_SCHEDULE_FULL,
    SEARCH_SCHEDULE_SELECTIVE,
    HandActionDecision,
    LiveHandActionDecisionEngine,
)


PPO_FULL_HORIZON_TACTICAL_SHADOW_SCHEMA = (
    "balatro-red-white-ppo-full-horizon-tactical-shadow-v1"
)
PPO_FULL_HORIZON_TACTICAL_REFERENCE_VERSION = (
    "balatro-red-white-full-horizon-tactical-reference-v1"
)
FULL_HORIZON_TACTICAL_SHADOW_REPORT_NAME = "full_horizon_tactical_shadow.json"


class PPOFullHorizonTacticalShadowError(ValueError):
    """Raised when full-horizon evidence or source provenance drifts."""


def _digest(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PPOFullHorizonTacticalShadowError(
            f"full-horizon {label} digest is invalid"
        )
    return value


def make_full_horizon_tactical_reference() -> LiveHandActionDecisionEngine:
    """Clone the production owner with only selective scheduling disabled."""

    production = make_ppo_tactical_decision_engine()
    if (
        production.search_schedule_mode != SEARCH_SCHEDULE_SELECTIVE
        or production.max_horizon != 8
        or production.max_search_nodes != 5000
        or production.exact_limit != 128
        or production.child_exact_limit != 8
        or production.max_search_seconds is not None
    ):
        raise PPOFullHorizonTacticalShadowError(
            "production tactical search contract drifted"
        )
    return LiveHandActionDecisionEngine(
        planner=production.planner,
        policy=production.policy,
        max_horizon=production.max_horizon,
        max_search_nodes=production.max_search_nodes,
        exact_limit=production.exact_limit,
        child_exact_limit=production.child_exact_limit,
        search_schedule_mode=SEARCH_SCHEDULE_FULL,
        max_search_seconds=production.max_search_seconds,
    )


def _action_signature(state, action) -> dict[str, Any]:
    positions = {id(card): index for index, card in enumerate(state.hand)}
    try:
        indices = [positions[id(card)] for card in action.cards]
    except KeyError as error:
        raise PPOFullHorizonTacticalShadowError(
            "full-horizon action escaped its public hand"
        ) from error
    target = getattr(action, "target", None)
    return {
        "name": action.name,
        "indices": indices,
        "target": None
        if target is None
        else str(getattr(target, "key", getattr(target, "name", target))),
    }


def _plan_record(state, plan) -> dict[str, Any] | None:
    if plan is None:
        return None
    return {
        "action": _action_signature(state, plan.action),
        "horizon": plan.horizon,
        "exact": plan.exact,
        "candidate_count": plan.candidate_count,
        "value": asdict(plan.value),
    }


class _RecordingFullHorizonEngine:
    def __init__(self, engine: LiveHandActionDecisionEngine) -> None:
        self.engine = engine
        self.decisions: list[dict[str, Any]] = []

    def decide(self, state) -> HandActionDecision:
        started = perf_counter()
        decision = self.engine.decide(state)
        elapsed = perf_counter() - started
        if not isinstance(decision, HandActionDecision):
            raise PPOFullHorizonTacticalShadowError(
                "full-horizon engine returned an invalid decision"
            )
        if not math.isfinite(elapsed) or elapsed < 0.0:
            raise PPOFullHorizonTacticalShadowError(
                "full-horizon decision timing is invalid"
            )
        blind = getattr(state, "blind", None)
        self.decisions.append(
            {
                "decision_index": len(self.decisions),
                "ante": int(state.ante),
                "round": int(state.round),
                "boss_name": getattr(state, "boss_name", None),
                "blind_requirement": int(getattr(blind, "requirement", 0)),
                "score": int(state.score),
                "hands_remaining": int(state.hands_remaining),
                "discards_remaining": int(state.discards_remaining),
                "mode": decision.mode,
                "action": _action_signature(state, decision.action),
                "selected_plan": _plan_record(state, decision.selected_plan),
                "search_attempts": [asdict(attempt) for attempt in decision.search_attempts],
                "completed_search_plans": [
                    _plan_record(state, plan)
                    for plan in decision.completed_search_plans
                ],
                "elapsed_seconds": elapsed,
            }
        )
        return decision


def _first_blind_cleared(frames) -> bool:
    trace = tuple(frames)
    if len(trace) < 2 or trace[0].state.phase != "BLIND_SELECT":
        raise PPOFullHorizonTacticalShadowError(
            "full-horizon frame trace does not begin at reset"
        )
    return any(frame.state.phase == "SHOP" for frame in trace[1:])


def _load_first_blind_production(path: str | Path) -> tuple[str, dict[int, bool]]:
    source = Path(path)
    try:
        raw = source.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PPOFullHorizonTacticalShadowError(
            "production first-blind source is unreadable"
        ) from error
    if (
        not isinstance(value, dict)
        or _canonical_bytes(value) != raw
        or value.get("schema_version") != PPO_TACTICAL_SHADOW_SCHEMA
        or value.get("corpus_sha256") != FIXED_SEEDED_CORPUS_SHA256
        or not isinstance(value.get("episodes"), list)
    ):
        raise PPOFullHorizonTacticalShadowError(
            "production first-blind source provenance drifted"
        )
    episodes = value["episodes"]
    expected = tuple(
        (spec.episode_index, spec.game_seed) for spec in FIXED_SEEDED_EPISODES
    )
    actual = tuple(
        (episode.get("episode_index"), episode.get("game_seed"))
        for episode in episodes
    )
    if actual != expected:
        raise PPOFullHorizonTacticalShadowError(
            "production first-blind source order drifted"
        )
    try:
        outcomes = {
            int(episode["episode_index"]): bool(episode["production"]["cleared"])
            for episode in episodes
        }
    except (KeyError, TypeError) as error:
        raise PPOFullHorizonTacticalShadowError(
            "production first-blind outcomes are malformed"
        ) from error
    return sha256(raw).hexdigest(), outcomes


def _execute_reference_episode(
    campaign: CompletedPPOCampaign,
    identity: PPOCandidateIdentity,
    spec: FixedSeededEpisodeSpec,
) -> dict[str, Any]:
    if (
        not isinstance(spec, FixedSeededEpisodeSpec)
        or FIXED_SEEDED_EPISODES[spec.episode_index] != spec
    ):
        raise PPOFullHorizonTacticalShadowError(
            "full-horizon episode spec drifted"
        )
    recorder: _RecordingFullHorizonEngine | None = None

    def factory(_stream_index):
        nonlocal recorder
        recorder = _RecordingFullHorizonEngine(
            make_full_horizon_tactical_reference()
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
        raise PPOFullHorizonTacticalShadowError(
            "full-horizon episode has no tactical decisions"
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
        raise PPOFullHorizonTacticalShadowError(
            "full-horizon worker is uninitialized"
        )
    return _execute_reference_episode(_WORKER_CAMPAIGN, _WORKER_IDENTITY, spec)


def _mean(episodes, arm: str, field: str) -> float:
    return fmean(float(item[arm]["metrics"][field]) for item in episodes)


def frozen_full_horizon_acceptance(
    episodes: tuple[dict[str, Any], ...],
    failure_counts: dict[str, int],
) -> dict[str, Any]:
    expected = tuple(
        (spec.episode_index, spec.game_seed, fixed_candidate_policy_seed(spec))
        for spec in FIXED_SEEDED_EPISODES
    )
    actual = tuple(
        (
            item.get("episode_index"),
            item.get("game_seed"),
            item.get("policy_seed"),
        )
        for item in episodes
    )
    canonical = actual == expected
    if not canonical:
        raise PPOFullHorizonTacticalShadowError(
            "full-horizon episodes are incomplete or out of order"
        )
    required_failures = {
        "illegal_action_count",
        "unsupported_mechanic_count",
        "truncated_episode_count",
        "incomplete_episode_count",
    }
    if (
        set(failure_counts) != required_failures
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in failure_counts.values()
        )
    ):
        raise PPOFullHorizonTacticalShadowError(
            "full-horizon failure counters are invalid"
        )
    production_clears = sum(
        item["production"]["status"] == "ANTE_8_WIN" for item in episodes
    )
    reference_clears = sum(
        item["reference"]["status"] == "ANTE_8_WIN" for item in episodes
    )
    production_first = sum(
        bool(item["production"]["first_blind_cleared"]) for item in episodes
    )
    reference_first = sum(
        bool(item["reference"]["first_blind_cleared"]) for item in episodes
    )
    gates = {
        "complete_canonical_evidence": canonical,
        "zero_fail_closed_outcomes": all(
            value == 0 for value in failure_counts.values()
        ),
        "first_blind_clear_count_nonregression": reference_first
        >= production_first,
        "full_game_clear_count_nonregression": reference_clears
        >= production_clears,
        "mean_ante_nonregression": _mean(episodes, "reference", "ante_reached")
        >= _mean(episodes, "production", "ante_reached"),
        "mean_requirement_progress_nonregression": _mean(
            episodes, "reference", "terminal_requirement_progress"
        )
        >= _mean(episodes, "production", "terminal_requirement_progress"),
        "mean_minimum_cash_nonregression": _mean(
            episodes, "reference", "minimum_money"
        )
        >= _mean(episodes, "production", "minimum_money"),
        "mean_terminal_cash_nonregression": _mean(
            episodes, "reference", "terminal_money"
        )
        >= _mean(episodes, "production", "terminal_money"),
    }
    strict = (
        reference_clears > production_clears
        or _mean(episodes, "reference", "ante_reached")
        > _mean(episodes, "production", "ante_reached")
        or _mean(episodes, "reference", "terminal_requirement_progress")
        > _mean(episodes, "production", "terminal_requirement_progress")
    )
    gates["strict_competence_improvement"] = strict
    accepted = all(gates.values())
    return {
        "production_first_blind_clears": production_first,
        "reference_first_blind_clears": reference_first,
        "production_full_game_clears": production_clears,
        "reference_full_game_clears": reference_clears,
        "production_mean_ante": _mean(episodes, "production", "ante_reached"),
        "reference_mean_ante": _mean(episodes, "reference", "ante_reached"),
        "production_mean_requirement_progress": _mean(
            episodes, "production", "terminal_requirement_progress"
        ),
        "reference_mean_requirement_progress": _mean(
            episodes, "reference", "terminal_requirement_progress"
        ),
        "production_mean_minimum_cash": _mean(
            episodes, "production", "minimum_money"
        ),
        "reference_mean_minimum_cash": _mean(
            episodes, "reference", "minimum_money"
        ),
        "production_mean_terminal_cash": _mean(
            episodes, "production", "terminal_money"
        ),
        "reference_mean_terminal_cash": _mean(
            episodes, "reference", "terminal_money"
        ),
        "reference_tactical_decision_count": sum(
            int(item["reference"]["tactical_decision_count"])
            for item in episodes
        ),
        "reference_tactical_elapsed_seconds": math.fsum(
            float(item["reference"]["tactical_elapsed_seconds"])
            for item in episodes
        ),
        "reference_maximum_tactical_decision_seconds": max(
            float(item["reference"]["maximum_tactical_decision_seconds"])
            for item in episodes
        ),
        "failure_counts": dict(failure_counts),
        "gates": gates,
        "accepted": accepted,
        "decision": "accept" if accepted else "reject",
    }


def run_full_horizon_tactical_shadow(
    campaign_directory: str | Path,
    promotion_directory: str | Path,
    production_first_blind_source: str | Path,
    output_path: str | Path,
    *,
    maximum_workers: int,
    episode_executor: Callable | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    destination = Path(output_path)
    if destination.exists():
        raise PPOFullHorizonTacticalShadowError(
            "full-horizon output already exists"
        )
    if not destination.parent.is_dir():
        raise PPOFullHorizonTacticalShadowError(
            "full-horizon output directory is missing"
        )
    if (
        isinstance(maximum_workers, bool)
        or not isinstance(maximum_workers, int)
        or not 1 <= maximum_workers <= 8
    ):
        raise PPOFullHorizonTacticalShadowError(
            "full-horizon workers must be from 1 through 8"
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
    published_metrics = {
        int(item["episode_index"]): item["metrics"]
        for item in diagnostics["episodes"]
    }

    reference_values: list[dict[str, Any]] = []

    def record(reference: dict[str, Any]) -> None:
        reference_values.append(reference)
        if progress_callback is not None:
            progress_callback(
                len(reference_values), len(FIXED_SEEDED_EPISODES)
            )

    if episode_executor is None:
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=maximum_workers,
            mp_context=context,
            initializer=_initialize_worker,
            initargs=(str(campaign_path),),
        ) as executor:
            for reference in executor.map(_worker, FIXED_SEEDED_EPISODES):
                record(reference)
    else:
        for spec in FIXED_SEEDED_EPISODES:
            record(episode_executor(campaign, identity, spec))

    episodes = []
    for spec, published, reference in zip(
        FIXED_SEEDED_EPISODES,
        candidate_source.episodes,
        reference_values,
        strict=True,
    ):
        if (
            reference.get("episode_index") != spec.episode_index
            or reference.get("game_seed") != spec.game_seed
            or published.episode_index != spec.episode_index
            or published.game_seed != spec.game_seed
        ):
            raise PPOFullHorizonTacticalShadowError(
                "full-horizon episode/source order drifted"
            )
        episodes.append(
            {
                "episode_index": spec.episode_index,
                "game_seed": spec.game_seed,
                "policy_seed": reference["policy_seed"],
                "production": {
                    "status": published.status.value,
                    "action_count": published.action_count,
                    "metrics": published_metrics[spec.episode_index],
                    "first_blind_cleared": production_first_blinds[
                        spec.episode_index
                    ],
                },
                "reference": reference,
            }
        )
    episodes_tuple = tuple(episodes)
    failure_counts = {
        "illegal_action_count": 0,
        "unsupported_mechanic_count": 0,
        "truncated_episode_count": 0,
        "incomplete_episode_count": 0,
    }
    report = {
        "schema_version": PPO_FULL_HORIZON_TACTICAL_SHADOW_SCHEMA,
        "reference_version": PPO_FULL_HORIZON_TACTICAL_REFERENCE_VERSION,
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
        "corpus_version": FIXED_SEEDED_CORPUS_VERSION,
        "corpus_sha256": FIXED_SEEDED_CORPUS_SHA256,
        "reference_config": {
            "search_schedule_mode": SEARCH_SCHEDULE_FULL,
            "maximum_useful_horizon": LIVE_ADAPTIVE_MAX_HORIZON,
            "max_search_nodes": 5000,
            "exact_combination_limit": 128,
            "child_exact_combination_limit": 8,
            "max_search_seconds": None,
        },
        "episodes": episodes,
        "summary": frozen_full_horizon_acceptance(
            episodes_tuple, failure_counts
        ),
    }
    _atomic_write(destination, _canonical_bytes(report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-directory", required=True)
    parser.add_argument("--promotion-directory", required=True)
    parser.add_argument("--production-first-blind-source", required=True)
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

    report = run_full_horizon_tactical_shadow(
        arguments.campaign_directory,
        arguments.promotion_directory,
        arguments.production_first_blind_source,
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
                "summary": report["summary"],
            }
        ).decode("utf-8")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
