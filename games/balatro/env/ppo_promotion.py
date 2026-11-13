"""Canonical diagnostics and frozen promotion decision for a trained PPO candidate."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from statistics import fmean
from typing import Any, Iterable, Mapping

from games.balatro.env.evaluation_diagnostics import (
    EvaluationDiagnosticsReport,
    TerminalEpisodeMetrics,
    derive_terminal_episode_metrics,
)
from games.balatro.env.ppo_candidate_evaluation import (
    FIXED_EVIDENCE_KIND,
    UNSEEDED_EVIDENCE_KIND,
    PPO_CANDIDATE_FIXED_REPORT_SCHEMA,
    PPO_CANDIDATE_UNSEEDED_REPORT_SCHEMA,
    PPOCandidateEpisodeEvidence,
    PPOCandidateFixedReport,
    PPOCandidateIdentity,
    PPOCandidateUnseededReport,
    execute_ppo_candidate_episode,
    run_fixed_ppo_candidate_evaluation,
    run_unseeded_ppo_candidate_evaluation,
)
from games.balatro.env.ppo_campaign import (
    CompletedPPOCampaign,
    make_ppo_training_environment,
)
from games.balatro.env.promotion_contract import (
    B0_PROMOTION_CONTRACT,
    B0_PROMOTION_CONTRACT_VERSION,
    ZERO_TOLERANCE_PATHOLOGIES,
)
from games.balatro.env.seeded_evaluation import (
    EVALUATED_BASELINE_VERSIONS,
    FIXED_SEEDED_CORPUS_SHA256,
)
from games.balatro.env.state import RunStatus
from games.balatro.env.unseeded_evaluation import UnseededEvaluationManifest


PPO_CANDIDATE_DIAGNOSTICS_SCHEMA = "balatro-ppo-candidate-diagnostics-v1"
PPO_CANDIDATE_DIAGNOSTICS_REPORT_SCHEMA = "balatro-ppo-candidate-diagnostics-report-v1"
PPO_PROMOTION_REPORT_SCHEMA = "balatro-ppo-promotion-report-v1"
_ONE_SIDED_95_Z = 1.6448536269514722


class PPOPromotionError(ValueError):
    """Raised when evaluation evidence cannot support an exact promotion decision."""


@dataclass(frozen=True)
class PPOCandidateEpisodeDiagnostics:
    schema_version: str
    candidate_sha256: str
    evidence_kind: str
    evidence_sha256: str
    episode_index: int
    game_seed: str
    status: RunStatus
    metrics: TerminalEpisodeMetrics

    def __post_init__(self) -> None:
        if self.schema_version != PPO_CANDIDATE_DIAGNOSTICS_SCHEMA:
            raise PPOPromotionError("candidate diagnostics schema version mismatch")
        if self.evidence_kind not in (FIXED_EVIDENCE_KIND, UNSEEDED_EVIDENCE_KIND):
            raise PPOPromotionError("candidate diagnostics evidence kind is invalid")
        for value, name in (
            (self.candidate_sha256, "candidate"),
            (self.evidence_sha256, "evidence"),
        ):
            if (
                not isinstance(value, str)
                or len(value) != 64
                or value != value.lower()
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise PPOPromotionError(f"candidate diagnostics {name} digest is invalid")
        if isinstance(self.episode_index, bool) or not isinstance(self.episode_index, int):
            raise PPOPromotionError("candidate diagnostics episode index is invalid")
        if self.episode_index < 0 or not isinstance(self.game_seed, str) or not self.game_seed:
            raise PPOPromotionError("candidate diagnostics episode provenance is invalid")
        if not isinstance(self.status, RunStatus) or not self.status.terminal:
            raise PPOPromotionError("candidate diagnostics status must be terminal")
        if not isinstance(self.metrics, TerminalEpisodeMetrics):
            raise PPOPromotionError("candidate terminal metrics are invalid")
        if self.metrics.ante_8_cleared != (self.status is RunStatus.ANTE_8_WIN):
            raise PPOPromotionError("candidate diagnostics contradict terminal status")
        if self.status is RunStatus.ANTE_8_WIN and (
            self.metrics.ante_reached < 8
            or self.metrics.terminal_blind_score < self.metrics.terminal_blind_requirement
        ):
            raise PPOPromotionError("candidate win diagnostics are inconsistent")
        if self.status is RunStatus.LOSS and (
            self.metrics.terminal_blind_score >= self.metrics.terminal_blind_requirement
        ):
            raise PPOPromotionError("candidate loss diagnostics are inconsistent")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "candidate_sha256": self.candidate_sha256,
            "evidence_kind": self.evidence_kind,
            "evidence_sha256": self.evidence_sha256,
            "episode_index": self.episode_index,
            "game_seed": self.game_seed,
            "status": self.status.value,
            "metrics": asdict(self.metrics),
        }


def derive_ppo_candidate_diagnostics(
    identity: PPOCandidateIdentity,
    evidence: PPOCandidateEpisodeEvidence,
) -> PPOCandidateEpisodeDiagnostics:
    if not isinstance(identity, PPOCandidateIdentity):
        raise TypeError("identity must be PPOCandidateIdentity")
    if not isinstance(evidence, PPOCandidateEpisodeEvidence):
        raise TypeError("evidence must be PPOCandidateEpisodeEvidence")
    result = evidence.result
    if result.candidate_sha256 != identity.sha256:
        raise PPOPromotionError("candidate diagnostic identity drifted")
    metrics = derive_terminal_episode_metrics(
        status=result.status,
        action_count=result.action_count,
        frames=evidence.frames,
    )
    return PPOCandidateEpisodeDiagnostics(
        schema_version=PPO_CANDIDATE_DIAGNOSTICS_SCHEMA,
        candidate_sha256=identity.sha256,
        evidence_kind=result.evidence_kind,
        evidence_sha256=result.evidence_sha256,
        episode_index=result.episode_index,
        game_seed=result.game_seed,
        status=result.status,
        metrics=metrics,
    )


@dataclass(frozen=True)
class PolicyMetricsSummary:
    episode_count: int
    ante_8_clears: int
    ante_8_clear_rate: float
    mean_ante_reached: float
    mean_terminal_requirement_progress: float
    mean_minimum_money: float
    mean_terminal_money: float


def _candidate_summary(
    episodes: tuple[PPOCandidateEpisodeDiagnostics, ...],
) -> PolicyMetricsSummary:
    if not episodes:
        raise PPOPromotionError("candidate diagnostics cannot be empty")
    clears = sum(item.metrics.ante_8_cleared for item in episodes)
    return PolicyMetricsSummary(
        episode_count=len(episodes),
        ante_8_clears=clears,
        ante_8_clear_rate=clears / len(episodes),
        mean_ante_reached=fmean(item.metrics.ante_reached for item in episodes),
        mean_terminal_requirement_progress=fmean(
            item.metrics.terminal_requirement_progress for item in episodes
        ),
        mean_minimum_money=fmean(item.metrics.minimum_money for item in episodes),
        mean_terminal_money=fmean(item.metrics.terminal_money for item in episodes),
    )


@dataclass(frozen=True)
class PPOCandidateDiagnosticsReport:
    schema_version: str
    source_schema_version: str
    source_sha256: str
    identity: PPOCandidateIdentity
    evidence_kind: str
    evidence_sha256: str
    episodes: tuple[PPOCandidateEpisodeDiagnostics, ...]
    summary: PolicyMetricsSummary

    def __post_init__(self) -> None:
        if self.schema_version != PPO_CANDIDATE_DIAGNOSTICS_REPORT_SCHEMA:
            raise PPOPromotionError("candidate diagnostics report schema mismatch")
        if not isinstance(self.identity, PPOCandidateIdentity):
            raise PPOPromotionError("candidate diagnostics report identity is invalid")
        expected_source = (
            PPO_CANDIDATE_FIXED_REPORT_SCHEMA
            if self.evidence_kind == FIXED_EVIDENCE_KIND
            else PPO_CANDIDATE_UNSEEDED_REPORT_SCHEMA
            if self.evidence_kind == UNSEEDED_EVIDENCE_KIND
            else None
        )
        if self.source_schema_version != expected_source:
            raise PPOPromotionError("candidate diagnostics source schema mismatch")
        for value, name in (
            (self.source_sha256, "source"),
            (self.evidence_sha256, "evidence"),
        ):
            if (
                not isinstance(value, str)
                or len(value) != 64
                or value != value.lower()
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise PPOPromotionError(f"candidate diagnostics {name} digest is invalid")
        if not isinstance(self.episodes, tuple) or not self.episodes:
            raise PPOPromotionError("candidate diagnostics report episodes are invalid")
        if any(
            not isinstance(item, PPOCandidateEpisodeDiagnostics)
            or item.candidate_sha256 != self.identity.sha256
            or item.evidence_kind != self.evidence_kind
            or item.evidence_sha256 != self.evidence_sha256
            for item in self.episodes
        ):
            raise PPOPromotionError("candidate diagnostics report provenance drifted")
        if self.summary != _candidate_summary(self.episodes):
            raise PPOPromotionError("candidate diagnostics summary is inconsistent")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_schema_version": self.source_schema_version,
            "source_sha256": self.source_sha256,
            "identity": self.identity.as_dict(),
            "evidence_kind": self.evidence_kind,
            "evidence_sha256": self.evidence_sha256,
            "episodes": [item.as_dict() for item in self.episodes],
            "summary": asdict(self.summary),
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))

    @property
    def episode_count(self) -> int:
        return len(self.episodes)


def aggregate_ppo_candidate_diagnostics(
    source: PPOCandidateFixedReport | PPOCandidateUnseededReport,
    episodes: Iterable[PPOCandidateEpisodeDiagnostics],
) -> PPOCandidateDiagnosticsReport:
    if not isinstance(source, (PPOCandidateFixedReport, PPOCandidateUnseededReport)):
        raise TypeError("source must be a PPO candidate evaluation report")
    values = tuple(episodes)
    if len(values) != len(source.episodes):
        raise PPOPromotionError("candidate diagnostics must cover every source episode")
    for result, diagnostic in zip(source.episodes, values, strict=True):
        if (
            not isinstance(diagnostic, PPOCandidateEpisodeDiagnostics)
            or diagnostic.candidate_sha256 != source.identity.sha256
            or diagnostic.evidence_kind != result.evidence_kind
            or diagnostic.evidence_sha256 != result.evidence_sha256
            or diagnostic.episode_index != result.episode_index
            or diagnostic.game_seed != result.game_seed
            or diagnostic.status is not result.status
        ):
            raise PPOPromotionError("candidate diagnostic does not match source episode")
    return PPOCandidateDiagnosticsReport(
        schema_version=PPO_CANDIDATE_DIAGNOSTICS_REPORT_SCHEMA,
        source_schema_version=source.schema_version,
        source_sha256=sha256(source.to_json().encode("utf-8")).hexdigest(),
        identity=source.identity,
        evidence_kind=values[0].evidence_kind,
        evidence_sha256=values[0].evidence_sha256,
        episodes=values,
        summary=_candidate_summary(values),
    )


@dataclass(frozen=True)
class PPOCandidateEvaluationBundle:
    """Complete candidate outcomes and diagnostics from one scheduled evidence set."""

    source: PPOCandidateFixedReport | PPOCandidateUnseededReport
    diagnostics: PPOCandidateDiagnosticsReport

    def __post_init__(self) -> None:
        if not isinstance(self.source, (PPOCandidateFixedReport, PPOCandidateUnseededReport)):
            raise PPOPromotionError("candidate evaluation bundle source is invalid")
        if not isinstance(self.diagnostics, PPOCandidateDiagnosticsReport):
            raise PPOPromotionError("candidate evaluation bundle diagnostics are invalid")
        expected = sha256(self.source.to_json().encode("utf-8")).hexdigest()
        if (
            self.diagnostics.identity != self.source.identity
            or self.diagnostics.source_schema_version != self.source.schema_version
            or self.diagnostics.source_sha256 != expected
        ):
            raise PPOPromotionError("candidate evaluation bundle provenance drifted")


def execute_fixed_ppo_candidate_evaluation(
    campaign: CompletedPPOCampaign,
    *,
    environment_factory=make_ppo_training_environment,
) -> PPOCandidateEvaluationBundle:
    """Execute the complete frozen fixed candidate arm with authoritative traces."""
    identity = PPOCandidateIdentity.from_completed_campaign(campaign)
    evidences: list[PPOCandidateEpisodeEvidence] = []

    def execute(actual_identity, spec, policy_seed):
        evidence = execute_ppo_candidate_episode(
            campaign,
            actual_identity,
            evidence_kind=FIXED_EVIDENCE_KIND,
            evidence_sha256=FIXED_SEEDED_CORPUS_SHA256,
            episode_index=spec.episode_index,
            game_seed=spec.game_seed,
            policy_seed=policy_seed,
            environment_factory=environment_factory,
        )
        evidences.append(evidence)
        return evidence.result

    source = run_fixed_ppo_candidate_evaluation(identity, execute)
    diagnostics = aggregate_ppo_candidate_diagnostics(
        source,
        tuple(derive_ppo_candidate_diagnostics(identity, item) for item in evidences),
    )
    return PPOCandidateEvaluationBundle(source, diagnostics)


def execute_unseeded_ppo_candidate_evaluation(
    campaign: CompletedPPOCampaign,
    manifest: UnseededEvaluationManifest,
    *,
    environment_factory=make_ppo_training_environment,
) -> PPOCandidateEvaluationBundle:
    """Execute one complete fresh-manifest candidate arm with authoritative traces."""
    if not isinstance(manifest, UnseededEvaluationManifest):
        raise TypeError("manifest must be UnseededEvaluationManifest")
    identity = PPOCandidateIdentity.from_completed_campaign(campaign)
    evidences: list[PPOCandidateEpisodeEvidence] = []

    def execute(actual_identity, spec, policy_seed):
        evidence = execute_ppo_candidate_episode(
            campaign,
            actual_identity,
            evidence_kind=UNSEEDED_EVIDENCE_KIND,
            evidence_sha256=manifest.manifest_sha256,
            episode_index=spec.episode_index,
            game_seed=spec.game_seed,
            policy_seed=policy_seed,
            environment_factory=environment_factory,
        )
        evidences.append(evidence)
        return evidence.result

    source = run_unseeded_ppo_candidate_evaluation(identity, manifest, execute)
    diagnostics = aggregate_ppo_candidate_diagnostics(
        source,
        tuple(derive_ppo_candidate_diagnostics(identity, item) for item in evidences),
    )
    return PPOCandidateEvaluationBundle(source, diagnostics)


def _wilson(successes: int, count: int) -> tuple[float, float]:
    if count <= 0 or successes < 0 or successes > count:
        raise PPOPromotionError("Wilson interval counts are invalid")
    rate = successes / count
    z2 = _ONE_SIDED_95_Z**2
    denominator = 1.0 + z2 / count
    center = (rate + z2 / (2.0 * count)) / denominator
    radius = _ONE_SIDED_95_Z * math.sqrt(
        rate * (1.0 - rate) / count + z2 / (4.0 * count**2)
    ) / denominator
    return max(0.0, center - radius), min(1.0, center + radius)


@dataclass(frozen=True)
class PromotionGate:
    name: str
    passed: bool
    actual: float
    threshold: float

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise PPOPromotionError("promotion gate name is invalid")
        if not isinstance(self.passed, bool):
            raise PPOPromotionError("promotion gate result is invalid")
        if not math.isfinite(float(self.actual)) or not math.isfinite(float(self.threshold)):
            raise PPOPromotionError("promotion gate values must be finite")
        expected = (
            self.actual == self.threshold
            if self.name.startswith("pathology:")
            else self.actual > self.threshold
            if self.name.startswith("unseeded_wilson_superiority:")
            else self.actual >= self.threshold
        )
        if self.passed != expected:
            raise PPOPromotionError("promotion gate result contradicts its values")


def _expected_gate_names() -> tuple[str, ...]:
    names = [
        *(f"fixed_clear_nonregression:{baseline}" for baseline in EVALUATED_BASELINE_VERSIONS),
        "unseeded_minimum_candidate_clear_rate",
    ]
    for baseline in EVALUATED_BASELINE_VERSIONS:
        names.extend((
            f"unseeded_clear_rate_delta:{baseline}",
            f"unseeded_wilson_superiority:{baseline}",
        ))
    for set_name in ("fixed", "unseeded_0", "unseeded_1", "unseeded_2", "unseeded_3"):
        for baseline in EVALUATED_BASELINE_VERSIONS:
            for metric in (
                "mean_ante_reached",
                "mean_terminal_requirement_progress",
                "mean_minimum_money",
                "mean_terminal_money",
            ):
                names.append(f"secondary:{set_name}:{baseline}:{metric}")
    names.extend(f"pathology:{name}" for name in ZERO_TOLERANCE_PATHOLOGIES)
    return tuple(names)


@dataclass(frozen=True)
class PPOPromotionReport:
    schema_version: str
    promotion_contract_version: str
    candidate_identity: PPOCandidateIdentity
    fixed_candidate_source_sha256: str
    fixed_baseline_source_sha256: str
    unseeded_candidate_source_sha256s: tuple[str, ...]
    unseeded_baseline_source_sha256s: tuple[str, ...]
    pathology_counts: tuple[tuple[str, int], ...]
    gates: tuple[PromotionGate, ...]
    promoted: bool

    def __post_init__(self) -> None:
        if self.schema_version != PPO_PROMOTION_REPORT_SCHEMA:
            raise PPOPromotionError("promotion report schema version mismatch")
        if self.promotion_contract_version != B0_PROMOTION_CONTRACT_VERSION:
            raise PPOPromotionError("promotion report contract version mismatch")
        if not isinstance(self.candidate_identity, PPOCandidateIdentity):
            raise PPOPromotionError("promotion report candidate identity is invalid")
        digests = (
            self.fixed_candidate_source_sha256,
            self.fixed_baseline_source_sha256,
            *self.unseeded_candidate_source_sha256s,
            *self.unseeded_baseline_source_sha256s,
        )
        if (
            len(self.unseeded_candidate_source_sha256s) != 4
            or len(self.unseeded_baseline_source_sha256s) != 4
            or any(
                not isinstance(value, str)
                or len(value) != 64
                or value != value.lower()
                or any(character not in "0123456789abcdef" for character in value)
                for value in digests
            )
        ):
            raise PPOPromotionError("promotion source digests are invalid")
        if tuple(name for name, _ in self.pathology_counts) != ZERO_TOLERANCE_PATHOLOGIES:
            raise PPOPromotionError("promotion pathology ordering drifted")
        if any(isinstance(count, bool) or not isinstance(count, int) or count < 0 for _, count in self.pathology_counts):
            raise PPOPromotionError("promotion pathology counts are invalid")
        if (
            not isinstance(self.gates, tuple)
            or any(not isinstance(gate, PromotionGate) for gate in self.gates)
            or tuple(gate.name for gate in self.gates) != _expected_gate_names()
        ):
            raise PPOPromotionError("promotion report gates are invalid")
        if self.promoted != all(gate.passed for gate in self.gates):
            raise PPOPromotionError("promotion decision contradicts its gates")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "promotion_contract_version": self.promotion_contract_version,
            "candidate_identity": self.candidate_identity.as_dict(),
            "fixed_candidate_source_sha256": self.fixed_candidate_source_sha256,
            "fixed_baseline_source_sha256": self.fixed_baseline_source_sha256,
            "unseeded_candidate_source_sha256s": list(self.unseeded_candidate_source_sha256s),
            "unseeded_baseline_source_sha256s": list(self.unseeded_baseline_source_sha256s),
            "pathology_counts": dict(self.pathology_counts),
            "gates": [asdict(gate) for gate in self.gates],
            "promoted": self.promoted,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


def _baseline_summary(report: EvaluationDiagnosticsReport, baseline: str):
    return next(item for item in report.baselines if item.baseline_version == baseline)


def _source_digest(report: EvaluationDiagnosticsReport) -> str:
    return sha256(report.to_json().encode("utf-8")).hexdigest()


def build_ppo_promotion_report(
    fixed_candidate: PPOCandidateDiagnosticsReport,
    fixed_baselines: EvaluationDiagnosticsReport,
    unseeded_candidates: Iterable[PPOCandidateDiagnosticsReport],
    unseeded_baselines: Iterable[EvaluationDiagnosticsReport],
    *,
    pathology_counts: Mapping[str, int],
) -> PPOPromotionReport:
    """Apply every frozen B0 gate to complete paired candidate/baseline evidence."""
    if not isinstance(fixed_candidate, PPOCandidateDiagnosticsReport):
        raise TypeError("fixed candidate diagnostics are invalid")
    if not isinstance(fixed_baselines, EvaluationDiagnosticsReport):
        raise TypeError("fixed baseline diagnostics are invalid")
    candidates = tuple(unseeded_candidates)
    baselines = tuple(unseeded_baselines)
    contract = B0_PROMOTION_CONTRACT
    if len(candidates) != contract.unseeded_manifests_per_arm or len(baselines) != len(candidates):
        raise PPOPromotionError("promotion requires exactly four paired unseeded manifests")
    if fixed_candidate.evidence_kind != FIXED_EVIDENCE_KIND or fixed_baselines.evidence_kind != FIXED_EVIDENCE_KIND:
        raise PPOPromotionError("fixed promotion evidence kind drifted")
    identity = fixed_candidate.identity
    for candidate, baseline in zip(candidates, baselines, strict=True):
        if not isinstance(candidate, PPOCandidateDiagnosticsReport) or not isinstance(baseline, EvaluationDiagnosticsReport):
            raise TypeError("unseeded promotion diagnostics are invalid")
        if candidate.identity != identity or candidate.evidence_kind != UNSEEDED_EVIDENCE_KIND:
            raise PPOPromotionError("unseeded candidate identity or evidence kind drifted")
        if baseline.evidence_kind != UNSEEDED_EVIDENCE_KIND or candidate.evidence_sha256 != baseline.evidence_sha256:
            raise PPOPromotionError("unseeded candidate/baseline manifest provenance drifted")
    manifest_digests = tuple(item.evidence_sha256 for item in candidates)
    if len(set(manifest_digests)) != len(manifest_digests):
        raise PPOPromotionError("unseeded promotion manifests must be unique")
    if set(pathology_counts) != set(ZERO_TOLERANCE_PATHOLOGIES):
        raise PPOPromotionError("promotion pathology audit is incomplete")
    pathology_values = tuple((name, pathology_counts[name]) for name in ZERO_TOLERANCE_PATHOLOGIES)

    gates: list[PromotionGate] = []
    for baseline_name in EVALUATED_BASELINE_VERSIONS:
        baseline = _baseline_summary(fixed_baselines, baseline_name)
        gates.append(PromotionGate(
            f"fixed_clear_nonregression:{baseline_name}",
            fixed_candidate.summary.ante_8_clears >= baseline.ante_8_clears,
            float(fixed_candidate.summary.ante_8_clears),
            float(baseline.ante_8_clears),
        ))

    candidate_episodes = tuple(item for report in candidates for item in report.episodes)
    candidate_summary = _candidate_summary(candidate_episodes)
    gates.append(PromotionGate(
        "unseeded_minimum_candidate_clear_rate",
        candidate_summary.ante_8_clear_rate >= contract.minimum_candidate_clear_rate,
        candidate_summary.ante_8_clear_rate,
        contract.minimum_candidate_clear_rate,
    ))
    candidate_lower, _ = _wilson(candidate_summary.ante_8_clears, candidate_summary.episode_count)
    for baseline_name in EVALUATED_BASELINE_VERSIONS:
        baseline_parts = tuple(_baseline_summary(report, baseline_name) for report in baselines)
        clears = sum(item.ante_8_clears for item in baseline_parts)
        count = sum(item.episode_count for item in baseline_parts)
        rate = clears / count
        _, upper = _wilson(clears, count)
        gates.extend((
            PromotionGate(
                f"unseeded_clear_rate_delta:{baseline_name}",
                candidate_summary.ante_8_clear_rate - rate >= contract.minimum_unseeded_clear_rate_delta,
                candidate_summary.ante_8_clear_rate - rate,
                contract.minimum_unseeded_clear_rate_delta,
            ),
            PromotionGate(
                f"unseeded_wilson_superiority:{baseline_name}",
                candidate_lower > upper,
                candidate_lower,
                upper,
            ),
        ))

    evidence_sets = (("fixed", fixed_candidate, fixed_baselines),) + tuple(
        (f"unseeded_{index}", candidate, baseline)
        for index, (candidate, baseline) in enumerate(zip(candidates, baselines, strict=True))
    )
    metric_gates = (
        ("mean_ante_reached", contract.maximum_mean_ante_regression),
        ("mean_terminal_requirement_progress", contract.maximum_mean_requirement_progress_regression),
        ("mean_minimum_money", contract.maximum_mean_minimum_money_regression),
        ("mean_terminal_money", contract.maximum_mean_terminal_money_regression),
    )
    for set_name, candidate, baseline_report in evidence_sets:
        for baseline_name in EVALUATED_BASELINE_VERSIONS:
            baseline = _baseline_summary(baseline_report, baseline_name)
            for metric, tolerance in metric_gates:
                delta = getattr(candidate.summary, metric) - getattr(baseline, metric)
                gates.append(PromotionGate(
                    f"secondary:{set_name}:{baseline_name}:{metric}",
                    delta >= -tolerance,
                    delta,
                    -tolerance,
                ))
    for name, count in pathology_values:
        gates.append(PromotionGate(f"pathology:{name}", count == 0, float(count), 0.0))

    values = tuple(gates)
    return PPOPromotionReport(
        schema_version=PPO_PROMOTION_REPORT_SCHEMA,
        promotion_contract_version=contract.version,
        candidate_identity=identity,
        fixed_candidate_source_sha256=fixed_candidate.source_sha256,
        fixed_baseline_source_sha256=_source_digest(fixed_baselines),
        unseeded_candidate_source_sha256s=tuple(item.source_sha256 for item in candidates),
        unseeded_baseline_source_sha256s=tuple(_source_digest(item) for item in baselines),
        pathology_counts=pathology_values,
        gates=values,
        promoted=all(gate.passed for gate in values),
    )
