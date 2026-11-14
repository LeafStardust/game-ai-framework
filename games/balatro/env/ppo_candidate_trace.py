"""Checkpoint-backed decision replay for failed fixed PPO promotion evidence."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable

from games.balatro.env.action_encoding import action_from_index
from games.balatro.env.actions import EnvAction
from games.balatro.env.ppo_campaign import (
    CompletedPPOCampaign,
    load_completed_ppo_campaign,
    make_ppo_training_environment,
)
from games.balatro.env.ppo_candidate_evaluation import (
    PPOCandidateDecision,
    PPOCandidateEpisodeResult,
    PPOCandidateFixedReport,
    PPOCandidateIdentity,
    execute_ppo_candidate_episode,
    fixed_candidate_policy_seed,
)
from games.balatro.env.ppo_contract import PPO_TRAINING_CONTRACT
from games.balatro.env.ppo_promotion_evaluation import (
    BaselineEpisodeEvidence,
    PPO_PROMOTION_PUBLICATION_VERSION,
    execute_baseline_episode,
)
from games.balatro.env.seeded_evaluation import (
    EVALUATED_BASELINE_VERSIONS,
    FIXED_SEEDED_CORPUS_SHA256,
    FIXED_SEEDED_EPISODES,
    FixedSeededEpisodeResult,
    FixedSeededEvaluationReport,
)
from games.balatro.env.state import EnvStateFrame, RunStatus


PPO_CANDIDATE_TRACE_SCHEMA = "balatro-ppo-candidate-fixed-trace-v1"
FIXED_EVIDENCE_KIND = "FIXED_SEEDED"


class PPOCandidateTraceError(ValueError):
    """Raised when published evidence cannot be replayed exactly."""


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise PPOCandidateTraceError("candidate trace is not canonical JSON") from error


def _digest(content: bytes) -> str:
    return sha256(content).hexdigest()


def _require_digest(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PPOCandidateTraceError(f"{name} is not a lowercase SHA-256 digest")
    return value


def _action_dict(action: EnvAction) -> dict[str, Any]:
    return {"alias": action.alias, "params": dict(action.params)}


def _frame_dict(frame: EnvStateFrame) -> dict[str, Any]:
    blind = frame.state.blind
    return {
        "phase": frame.state.phase,
        "ante": frame.state.ante,
        "round": frame.state.round,
        "money": frame.state.money,
        "score": frame.state.score,
        "blind_requirement": None if blind is None else blind.requirement,
        "status": frame.status.value,
    }


@dataclass(frozen=True)
class CandidateDecisionTrace:
    decision_index: int
    frame: dict[str, Any]
    observation_schema: str
    observation_values: tuple[float, ...]
    observation_sha256: str
    action_mask: tuple[bool, ...]
    probabilities: tuple[float, ...]
    value_estimate: float
    selected_action_index: int
    selected_action: dict[str, Any]

    def __post_init__(self) -> None:
        if (
            isinstance(self.decision_index, bool)
            or not isinstance(self.decision_index, int)
            or self.decision_index < 0
        ):
            raise PPOCandidateTraceError("trace decision index is invalid")
        if self.observation_schema != PPO_TRAINING_CONTRACT.observation_version:
            raise PPOCandidateTraceError("trace observation schema drifted")
        if len(self.observation_values) != PPO_TRAINING_CONTRACT.observation_size:
            raise PPOCandidateTraceError("trace observation shape drifted")
        _require_digest(self.observation_sha256, "trace observation digest")
        expected_digest = _digest(_canonical_bytes({
            "schema_version": self.observation_schema,
            "values": self.observation_values,
        }))
        if self.observation_sha256 != expected_digest:
            raise PPOCandidateTraceError("trace observation digest mismatches values")
        if (
            len(self.action_mask) != PPO_TRAINING_CONTRACT.action_size
            or len(self.probabilities) != PPO_TRAINING_CONTRACT.action_size
            or not 0 <= self.selected_action_index < PPO_TRAINING_CONTRACT.action_size
            or not self.action_mask[self.selected_action_index]
        ):
            raise PPOCandidateTraceError("trace action evidence is invalid")
        if any(
            not math.isfinite(value) or value < 0.0
            for value in self.probabilities
        ) or not math.isclose(sum(self.probabilities), 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise PPOCandidateTraceError("trace probabilities are invalid")
        if any(probability != 0.0 for probability, allowed in zip(
            self.probabilities, self.action_mask, strict=True
        ) if not allowed):
            raise PPOCandidateTraceError("trace assigns mass to an illegal action")
        if not math.isfinite(self.value_estimate):
            raise PPOCandidateTraceError("trace value estimate is non-finite")
        expected_action = action_from_index(self.selected_action_index)
        if self.selected_action != _action_dict(expected_action):
            raise PPOCandidateTraceError("trace selected action index drifted")

    @classmethod
    def from_decision(
        cls,
        decision: PPOCandidateDecision,
        frame: EnvStateFrame,
    ) -> "CandidateDecisionTrace":
        if not isinstance(decision, PPOCandidateDecision):
            raise TypeError("decision must be PPOCandidateDecision")
        observation_payload = {
            "schema_version": decision.observation.schema_version,
            "values": decision.observation.values,
        }
        return cls(
            decision_index=decision.decision_index,
            frame=_frame_dict(frame),
            observation_schema=decision.observation.schema_version,
            observation_values=decision.observation.values,
            observation_sha256=_digest(_canonical_bytes(observation_payload)),
            action_mask=decision.action_mask.values,
            probabilities=decision.probabilities,
            value_estimate=decision.value_estimate,
            selected_action_index=decision.action_index,
            selected_action=_action_dict(decision.action),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision_index": self.decision_index,
            "frame": self.frame,
            "observation_schema": self.observation_schema,
            "observation_values": list(self.observation_values),
            "observation_sha256": self.observation_sha256,
            "action_mask": list(self.action_mask),
            "probabilities": list(self.probabilities),
            "value_estimate": self.value_estimate,
            "selected_action_index": self.selected_action_index,
            "selected_action": self.selected_action,
        }


@dataclass(frozen=True)
class BaselineReplayTrace:
    baseline_version: str
    expected_status: RunStatus
    expected_action_count: int
    actions: tuple[EnvAction, ...]
    frames: tuple[dict[str, Any], ...]

    def __post_init__(self) -> None:
        if self.baseline_version not in EVALUATED_BASELINE_VERSIONS:
            raise PPOCandidateTraceError("trace baseline version is invalid")
        if not isinstance(self.expected_status, RunStatus) or not self.expected_status.terminal:
            raise PPOCandidateTraceError("trace baseline status is invalid")
        if len(self.actions) != self.expected_action_count:
            raise PPOCandidateTraceError("trace baseline actions are incomplete")
        if len(self.frames) != self.expected_action_count + 1:
            raise PPOCandidateTraceError("trace baseline frames are incomplete")

    @classmethod
    def completed(
        cls,
        expected: FixedSeededEpisodeResult,
        replay: BaselineEpisodeEvidence,
    ) -> "BaselineReplayTrace":
        if (
            replay.baseline_version != expected.baseline_version
            or replay.game_seed != expected.game_seed
            or replay.policy_seed != expected.policy_seed
            or replay.status is not expected.status
            or replay.action_count != expected.action_count
            or len(replay.actions) != replay.action_count
        ):
            raise PPOCandidateTraceError("baseline replay drifted from published evidence")
        return cls(
            baseline_version=expected.baseline_version,
            expected_status=expected.status,
            expected_action_count=expected.action_count,
            actions=replay.actions,
            frames=tuple(_frame_dict(frame) for frame in replay.frames),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "baseline_version": self.baseline_version,
            "expected_status": self.expected_status.value,
            "expected_action_count": self.expected_action_count,
            "actions": [_action_dict(action) for action in self.actions],
            "frames": list(self.frames),
        }


@dataclass(frozen=True)
class FixedCandidateTraceEpisode:
    episode_index: int
    game_seed: str
    policy_seed: str
    expected_status: RunStatus
    expected_action_count: int
    decisions: tuple[CandidateDecisionTrace, ...]
    frames: tuple[dict[str, Any], ...]
    baselines: tuple[BaselineReplayTrace, ...]

    def __post_init__(self) -> None:
        if len(self.decisions) != self.expected_action_count:
            raise PPOCandidateTraceError("candidate replay decisions are incomplete")
        if len(self.frames) != self.expected_action_count + 1:
            raise PPOCandidateTraceError("candidate replay frames are incomplete")
        if tuple(item.decision_index for item in self.decisions) != tuple(
            range(self.expected_action_count)
        ):
            raise PPOCandidateTraceError("candidate replay decision order drifted")
        if tuple(item.baseline_version for item in self.baselines) != EVALUATED_BASELINE_VERSIONS:
            raise PPOCandidateTraceError("candidate replay baselines are incomplete")

    def as_dict(self) -> dict[str, Any]:
        return {
            "episode_index": self.episode_index,
            "game_seed": self.game_seed,
            "policy_seed": self.policy_seed,
            "expected_status": self.expected_status.value,
            "expected_action_count": self.expected_action_count,
            "decisions": [item.as_dict() for item in self.decisions],
            "frames": list(self.frames),
            "baselines": [item.as_dict() for item in self.baselines],
        }


@dataclass(frozen=True)
class FixedCandidateTraceReport:
    schema_version: str
    candidate_identity: PPOCandidateIdentity
    evaluation_sha256: str
    promotion_report_sha256: str
    fixed_candidate_source_sha256: str
    fixed_baseline_source_sha256: str
    episode_indices: tuple[int, ...]
    episodes: tuple[FixedCandidateTraceEpisode, ...]

    def __post_init__(self) -> None:
        if self.schema_version != PPO_CANDIDATE_TRACE_SCHEMA:
            raise PPOCandidateTraceError("candidate trace schema version mismatch")
        if not isinstance(self.candidate_identity, PPOCandidateIdentity):
            raise PPOCandidateTraceError("candidate trace identity is invalid")
        for value, name in (
            (self.evaluation_sha256, "evaluation digest"),
            (self.promotion_report_sha256, "promotion report digest"),
            (self.fixed_candidate_source_sha256, "candidate source digest"),
            (self.fixed_baseline_source_sha256, "baseline source digest"),
        ):
            _require_digest(value, name)
        if (
            not isinstance(self.episode_indices, tuple)
            or not self.episode_indices
            or len(set(self.episode_indices)) != len(self.episode_indices)
            or tuple(item.episode_index for item in self.episodes) != self.episode_indices
        ):
            raise PPOCandidateTraceError("candidate trace episode ordering drifted")

    @property
    def selected_action_counts(self) -> tuple[tuple[str, int], ...]:
        counts = Counter(
            decision.selected_action["alias"]
            for episode in self.episodes
            for decision in episode.decisions
        )
        return tuple(sorted(counts.items()))

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "candidate_identity": self.candidate_identity.as_dict(),
            "evaluation_sha256": self.evaluation_sha256,
            "promotion_report_sha256": self.promotion_report_sha256,
            "fixed_candidate_source_sha256": self.fixed_candidate_source_sha256,
            "fixed_baseline_source_sha256": self.fixed_baseline_source_sha256,
            "episode_indices": list(self.episode_indices),
            "selected_action_counts": dict(self.selected_action_counts),
            "episodes": [item.as_dict() for item in self.episodes],
        }

    def to_json(self) -> str:
        return _canonical_bytes(self.as_dict()).decode("utf-8")

    @property
    def sha256(self) -> str:
        return _digest(self.to_json().encode("utf-8"))


def select_fixed_trace_episode_indices(
    source: PPOCandidateFixedReport,
) -> tuple[int, ...]:
    if not isinstance(source, PPOCandidateFixedReport):
        raise TypeError("source must be PPOCandidateFixedReport")
    minimum = min(item.action_count for item in source.episodes)
    early = tuple(
        item.episode_index for item in source.episodes if item.action_count == minimum
    )[:2]
    longest = max(source.episodes, key=lambda item: (item.action_count, -item.episode_index))
    selected = (*early, longest.episode_index)
    if len(early) != 2 or len(set(selected)) != 3:
        raise PPOCandidateTraceError("published evidence cannot pin representative traces")
    return selected


def build_fixed_candidate_trace_report(
    campaign: CompletedPPOCampaign,
    candidate_source: PPOCandidateFixedReport,
    baseline_source: FixedSeededEvaluationReport,
    *,
    evaluation_sha256: str,
    promotion_report_sha256: str,
    fixed_candidate_source_sha256: str,
    fixed_baseline_source_sha256: str,
    episode_indices: Iterable[int] | None = None,
    environment_factory=make_ppo_training_environment,
    symbolic_decider=None,
) -> FixedCandidateTraceReport:
    if not isinstance(campaign, CompletedPPOCampaign):
        raise TypeError("campaign must be CompletedPPOCampaign")
    identity = PPOCandidateIdentity.from_completed_campaign(campaign)
    if candidate_source.identity != identity:
        raise PPOCandidateTraceError("trace candidate source identity drifted")
    if not isinstance(baseline_source, FixedSeededEvaluationReport):
        raise TypeError("baseline_source must be FixedSeededEvaluationReport")
    indices = (
        select_fixed_trace_episode_indices(candidate_source)
        if episode_indices is None
        else tuple(episode_indices)
    )
    if any(
        isinstance(index, bool)
        or not isinstance(index, int)
        or not 0 <= index < len(FIXED_SEEDED_EPISODES)
        for index in indices
    ):
        raise PPOCandidateTraceError("trace episode index is invalid")

    episodes: list[FixedCandidateTraceEpisode] = []
    for index in indices:
        spec = FIXED_SEEDED_EPISODES[index]
        expected = candidate_source.episodes[index]
        replay = execute_ppo_candidate_episode(
            campaign,
            identity,
            evidence_kind=FIXED_EVIDENCE_KIND,
            evidence_sha256=FIXED_SEEDED_CORPUS_SHA256,
            episode_index=index,
            game_seed=spec.game_seed,
            policy_seed=fixed_candidate_policy_seed(spec),
            environment_factory=environment_factory,
        )
        if replay.result != expected or len(replay.decisions) != expected.action_count:
            raise PPOCandidateTraceError("candidate replay drifted from published evidence")
        decision_traces = tuple(
            CandidateDecisionTrace.from_decision(decision, replay.frames[position])
            for position, decision in enumerate(replay.decisions)
        )
        baseline_traces = []
        for baseline in EVALUATED_BASELINE_VERSIONS:
            expected_baseline = next(
                item
                for item in baseline_source.episodes
                if item.baseline_version == baseline and item.episode_index == index
            )
            kwargs = {}
            if symbolic_decider is not None:
                kwargs["symbolic_decider"] = symbolic_decider
            baseline_replay = execute_baseline_episode(
                baseline,
                game_seed=spec.game_seed,
                policy_seed=spec.policy_seed(baseline),
                environment_factory=environment_factory,
                **kwargs,
            )
            baseline_traces.append(
                BaselineReplayTrace.completed(expected_baseline, baseline_replay)
            )
        episodes.append(FixedCandidateTraceEpisode(
            episode_index=index,
            game_seed=spec.game_seed,
            policy_seed=fixed_candidate_policy_seed(spec),
            expected_status=expected.status,
            expected_action_count=expected.action_count,
            decisions=decision_traces,
            frames=tuple(_frame_dict(frame) for frame in replay.frames),
            baselines=tuple(baseline_traces),
        ))
    return FixedCandidateTraceReport(
        schema_version=PPO_CANDIDATE_TRACE_SCHEMA,
        candidate_identity=identity,
        evaluation_sha256=evaluation_sha256,
        promotion_report_sha256=promotion_report_sha256,
        fixed_candidate_source_sha256=fixed_candidate_source_sha256,
        fixed_baseline_source_sha256=fixed_baseline_source_sha256,
        episode_indices=indices,
        episodes=tuple(episodes),
    )


def _candidate_result(payload: dict[str, Any]) -> PPOCandidateEpisodeResult:
    value = dict(payload)
    value["status"] = RunStatus(value["status"])
    return PPOCandidateEpisodeResult(**value)


def _baseline_result(payload: dict[str, Any]) -> FixedSeededEpisodeResult:
    value = dict(payload)
    value["status"] = RunStatus(value["status"])
    return FixedSeededEpisodeResult(**value)


def load_published_fixed_sources(
    campaign: CompletedPPOCampaign,
    promotion_directory: str | Path,
) -> tuple[dict[str, Any], PPOCandidateFixedReport, FixedSeededEvaluationReport]:
    if not isinstance(campaign, CompletedPPOCampaign):
        raise TypeError("campaign must be CompletedPPOCampaign")
    directory = Path(promotion_directory)
    final_path = directory / "final.json"
    if not final_path.is_file():
        raise PPOCandidateTraceError("published promotion final artifact is missing")
    final_bytes = final_path.read_bytes()
    try:
        final = json.loads(final_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PPOCandidateTraceError("published promotion final artifact is invalid") from error
    if final_bytes != _canonical_bytes(final):
        raise PPOCandidateTraceError("published promotion final artifact is noncanonical")
    identity = PPOCandidateIdentity.from_completed_campaign(campaign)
    if final.get("version") != PPO_PROMOTION_PUBLICATION_VERSION:
        raise PPOCandidateTraceError("published promotion version drifted")
    if final.get("candidate_sha256") != identity.sha256:
        raise PPOCandidateTraceError("published promotion candidate identity drifted")
    artifacts = final.get("artifacts")
    required = ("fixed-candidate.json", "fixed-baselines.json", "promotion.json")
    if not isinstance(artifacts, dict) or any(name not in artifacts for name in required):
        raise PPOCandidateTraceError("published promotion source index is incomplete")
    if (
        final.get("promotion_report_sha256") != artifacts["promotion.json"]
        or not isinstance(final.get("promoted"), bool)
    ):
        raise PPOCandidateTraceError("published promotion final linkage drifted")
    payloads = {}
    for name in required:
        content = (directory / name).read_bytes()
        if _digest(content) != artifacts[name]:
            raise PPOCandidateTraceError("published promotion source digest mismatch")
        try:
            payloads[name] = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PPOCandidateTraceError("published promotion source is invalid") from error
        if content != _canonical_bytes(payloads[name]):
            raise PPOCandidateTraceError("published promotion source is noncanonical")

    candidate_payload = payloads["fixed-candidate.json"]
    if candidate_payload.get("identity") != identity.as_dict():
        raise PPOCandidateTraceError("published fixed candidate identity drifted")
    candidate_source = PPOCandidateFixedReport(
        schema_version=candidate_payload["schema_version"],
        identity=identity,
        episodes=tuple(_candidate_result(item) for item in candidate_payload["episodes"]),
    )
    baseline_payload = payloads["fixed-baselines.json"]
    baseline_source = FixedSeededEvaluationReport(
        schema_version=baseline_payload["schema_version"],
        corpus_version=baseline_payload["corpus_version"],
        corpus_sha256=baseline_payload["corpus_sha256"],
        episodes=tuple(_baseline_result(item) for item in baseline_payload["episodes"]),
    )
    return final, candidate_source, baseline_source


def replay_published_fixed_candidate_traces(
    campaign: CompletedPPOCampaign,
    promotion_directory: str | Path,
    *,
    environment_factory=make_ppo_training_environment,
    symbolic_decider=None,
) -> FixedCandidateTraceReport:
    final, candidate_source, baseline_source = load_published_fixed_sources(
        campaign, promotion_directory
    )
    return build_fixed_candidate_trace_report(
        campaign,
        candidate_source,
        baseline_source,
        evaluation_sha256=final["evaluation_sha256"],
        promotion_report_sha256=final["promotion_report_sha256"],
        fixed_candidate_source_sha256=final["artifacts"]["fixed-candidate.json"],
        fixed_baseline_source_sha256=final["artifacts"]["fixed-baselines.json"],
        environment_factory=environment_factory,
        symbolic_decider=symbolic_decider,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Replay representative fixed PPO promotion failures exactly."
    )
    parser.add_argument("artifact_directory")
    parser.add_argument("promotion_directory")
    parser.add_argument("output_path")
    arguments = parser.parse_args(argv)
    campaign = load_completed_ppo_campaign(arguments.artifact_directory)
    report = replay_published_fixed_candidate_traces(
        campaign, arguments.promotion_directory
    )
    output = Path(arguments.output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_text(report.to_json(), encoding="utf-8", newline="")
    os.replace(temporary, output)
    print(json.dumps({
        "output_path": str(output.resolve()),
        "report_sha256": report.sha256,
        "episode_indices": list(report.episode_indices),
        "selected_action_counts": dict(report.selected_action_counts),
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
