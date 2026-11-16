"""Fixed-corpus shadow for stable-consensus sampled deep discards."""

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
from games.balatro.env.ppo_current_tactical_reproduction import (
    PPO_CURRENT_TACTICAL_REPRODUCTION_SCHEMA,
    first_tactical_divergence,
)
from games.balatro.env.ppo_full_horizon_tactical_shadow import (
    _RecordingFullHorizonEngine,
    _first_blind_cleared,
    frozen_full_horizon_acceptance,
)
from games.balatro.env.ppo_promotion_evaluation import FINAL_ARTIFACT_NAME
from games.balatro.env.seeded_evaluation import (
    FIXED_SEEDED_CORPUS_SHA256,
    FIXED_SEEDED_CORPUS_VERSION,
    FIXED_SEEDED_EPISODES,
    FixedSeededEpisodeSpec,
)
from games.balatro.live.adaptive_search import LIVE_ADAPTIVE_MAX_HORIZON
from games.balatro.live.hand_action_policy import (
    SEARCH_SCHEDULE_SELECTIVE,
    SEARCH_SCHEDULE_STABLE_DISCARD,
    LiveHandActionDecisionEngine,
)


PPO_STABLE_DISCARD_TACTICAL_SHADOW_SCHEMA = (
    "balatro-red-white-ppo-stable-discard-tactical-shadow-v1"
)
STABLE_DISCARD_TACTICAL_SHADOW_REPORT_NAME = (
    "stable_discard_tactical_shadow.json"
)
CURRENT_TACTICAL_REPRODUCTION_SOURCE_SHA256 = (
    "984ee7441025b6744bba988509bc2fa0ac35765acb85ccc4f77fa8ff42097ec8"
)


class PPOStableDiscardTacticalShadowError(ValueError):
    """Raised when stable-discard shadow evidence drifts."""


def make_stable_discard_tactical_reference() -> LiveHandActionDecisionEngine:
    """Clone production with only the explicit shadow schedule mode changed."""

    production = make_ppo_tactical_decision_engine()
    if (
        production.search_schedule_mode != SEARCH_SCHEDULE_SELECTIVE
        or production.max_horizon != 8
        or production.max_search_nodes != 5000
        or production.exact_limit != 128
        or production.child_exact_limit != 8
        or production.max_search_seconds is not None
    ):
        raise PPOStableDiscardTacticalShadowError(
            "production tactical search contract drifted"
        )
    return LiveHandActionDecisionEngine(
        planner=production.planner,
        policy=production.policy,
        max_horizon=production.max_horizon,
        max_search_nodes=production.max_search_nodes,
        exact_limit=production.exact_limit,
        child_exact_limit=production.child_exact_limit,
        search_schedule_mode=SEARCH_SCHEDULE_STABLE_DISCARD,
        max_search_seconds=production.max_search_seconds,
    )


class _RecordingStableDiscardEngine(_RecordingFullHorizonEngine):
    def decide(self, state):
        decision = super().decide(state)
        self.decisions[-1].update(
            {
                "setup_discard_consensus": decision.setup_discard_consensus,
                "sampled_clear_path_confirmed": (
                    decision.sampled_clear_path_confirmed
                ),
                "clear_path_candidates": decision.clear_path_candidates,
            }
        )
        return decision


def _execute_stable_discard_episode(
    campaign: CompletedPPOCampaign,
    identity: PPOCandidateIdentity,
    spec: FixedSeededEpisodeSpec,
) -> dict[str, Any]:
    if (
        not isinstance(spec, FixedSeededEpisodeSpec)
        or FIXED_SEEDED_EPISODES[spec.episode_index] != spec
    ):
        raise PPOStableDiscardTacticalShadowError(
            "stable-discard episode spec drifted"
        )
    recorder: _RecordingStableDiscardEngine | None = None

    def factory(_stream_index):
        nonlocal recorder
        recorder = _RecordingStableDiscardEngine(
            make_stable_discard_tactical_reference()
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
        raise PPOStableDiscardTacticalShadowError(
            "stable-discard episode has no tactical decisions"
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
        raise PPOStableDiscardTacticalShadowError(
            "stable-discard worker is uninitialized"
        )
    return _execute_stable_discard_episode(
        _WORKER_CAMPAIGN, _WORKER_IDENTITY, spec
    )


def _load_reproduction_source(
    path: str | Path,
) -> tuple[dict[str, Any], str]:
    source = Path(path)
    try:
        raw = source.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PPOStableDiscardTacticalShadowError(
            "current reproduction source is unreadable"
        ) from error
    digest = sha256(raw).hexdigest()
    comparison = value.get("comparison") if isinstance(value, dict) else None
    if (
        not isinstance(value, dict)
        or digest != CURRENT_TACTICAL_REPRODUCTION_SOURCE_SHA256
        or _canonical_bytes(value) != raw
        or value.get("schema_version")
        != PPO_CURRENT_TACTICAL_REPRODUCTION_SCHEMA
        or value.get("decision") != "published-exact"
        or value.get("corpus_version") != FIXED_SEEDED_CORPUS_VERSION
        or value.get("corpus_sha256") != FIXED_SEEDED_CORPUS_SHA256
        or not isinstance(value.get("episodes"), list)
        or not isinstance(comparison, dict)
        or comparison.get("published_reproduction_exact") is not True
        or comparison.get("published_mismatch_count") != 0
    ):
        raise PPOStableDiscardTacticalShadowError(
            "current reproduction source provenance drifted"
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
        raise PPOStableDiscardTacticalShadowError(
            "current reproduction source order drifted"
        )
    return value, digest


def run_stable_discard_tactical_shadow(
    campaign_directory: str | Path,
    promotion_directory: str | Path,
    current_reproduction_source: str | Path,
    output_path: str | Path,
    *,
    maximum_workers: int,
    episode_executor: Callable | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    destination = Path(output_path)
    if destination.exists():
        raise PPOStableDiscardTacticalShadowError(
            "stable-discard output already exists"
        )
    if not destination.parent.is_dir():
        raise PPOStableDiscardTacticalShadowError(
            "stable-discard output directory is missing"
        )
    if (
        isinstance(maximum_workers, bool)
        or not isinstance(maximum_workers, int)
        or not 1 <= maximum_workers <= 8
    ):
        raise PPOStableDiscardTacticalShadowError(
            "stable-discard workers must be from 1 through 8"
        )
    if episode_executor is not None and not callable(episode_executor):
        raise TypeError("episode_executor must be callable")
    if progress_callback is not None and not callable(progress_callback):
        raise TypeError("progress_callback must be callable")

    campaign_path = Path(campaign_directory)
    promotion_path = Path(promotion_directory)
    campaign = load_completed_ppo_campaign(campaign_path)
    identity = PPOCandidateIdentity.from_completed_campaign(campaign)
    reproduction, reproduction_sha256 = _load_reproduction_source(
        current_reproduction_source
    )
    expected_links = {
        "candidate_sha256": identity.sha256,
        "campaign_checkpoint_sha256": campaign.checkpoint_sha256,
        "campaign_progress_sha256": campaign.progress_sha256,
        "campaign_final_sha256": campaign.final_sha256,
        "promotion_final_sha256": sha256(
            (promotion_path / FINAL_ARTIFACT_NAME).read_bytes()
        ).hexdigest(),
    }
    if any(reproduction.get(key) != value for key, value in expected_links.items()):
        raise PPOStableDiscardTacticalShadowError(
            "current reproduction source links drifted"
        )

    reference_values: list[dict[str, Any]] = []

    def record(value: dict[str, Any]) -> None:
        reference_values.append(value)
        if progress_callback is not None:
            progress_callback(len(reference_values), len(FIXED_SEEDED_EPISODES))

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
    divergence_count = 0
    consensus_decision_count = 0
    for spec, baseline_episode, reference in zip(
        FIXED_SEEDED_EPISODES,
        reproduction["episodes"],
        reference_values,
        strict=True,
    ):
        baseline = baseline_episode["current_selective"]
        if (
            reference.get("episode_index") != spec.episode_index
            or reference.get("game_seed") != spec.game_seed
            or baseline_episode.get("episode_index") != spec.episode_index
            or baseline_episode.get("game_seed") != spec.game_seed
        ):
            raise PPOStableDiscardTacticalShadowError(
                "stable-discard episode/source order drifted"
            )
        divergence = first_tactical_divergence(baseline, reference)
        if divergence is not None:
            divergence_count += 1
        consensus_decision_count += sum(
            bool(decision["setup_discard_consensus"])
            for decision in reference["decisions"]
        )
        episodes.append(
            {
                "episode_index": spec.episode_index,
                "game_seed": spec.game_seed,
                "policy_seed": reference["policy_seed"],
                "production": {
                    key: baseline[key]
                    for key in (
                        "status",
                        "action_count",
                        "metrics",
                        "first_blind_cleared",
                    )
                },
                "reference": reference,
                "first_divergence": divergence,
            }
        )
    failures = {
        "illegal_action_count": 0,
        "unsupported_mechanic_count": 0,
        "truncated_episode_count": 0,
        "incomplete_episode_count": 0,
    }
    summary = frozen_full_horizon_acceptance(tuple(episodes), failures)
    summary.update(
        {
            "trajectory_divergence_count": divergence_count,
            "stable_discard_consensus_decision_count": (
                consensus_decision_count
            ),
        }
    )
    report = {
        "schema_version": PPO_STABLE_DISCARD_TACTICAL_SHADOW_SCHEMA,
        **expected_links,
        "current_reproduction_source_sha256": reproduction_sha256,
        "corpus_version": FIXED_SEEDED_CORPUS_VERSION,
        "corpus_sha256": FIXED_SEEDED_CORPUS_SHA256,
        "reference_config": {
            "search_schedule_mode": SEARCH_SCHEDULE_STABLE_DISCARD,
            "maximum_useful_horizon": LIVE_ADAPTIVE_MAX_HORIZON,
            "max_search_nodes": 5000,
            "exact_combination_limit": 128,
            "child_exact_combination_limit": 8,
            "sampled_discard_minimum_consensus": 3,
            "max_search_seconds": None,
        },
        "episodes": episodes,
        "summary": summary,
    }
    _atomic_write(destination, _canonical_bytes(report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-directory", required=True)
    parser.add_argument("--promotion-directory", required=True)
    parser.add_argument("--current-reproduction-source", required=True)
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

    report = run_stable_discard_tactical_shadow(
        arguments.campaign_directory,
        arguments.promotion_directory,
        arguments.current_reproduction_source,
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
