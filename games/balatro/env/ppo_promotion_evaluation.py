"""Atomic execution and publication owner for the frozen PPO promotion run."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
from typing import Any
from uuid import uuid4

from games.balatro.actions import BalatroAction
from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.episode_backend import PPO_HEADLESS_BACKEND_SCHEMA
from games.balatro.env.evaluation_diagnostics import (
    EvaluationDiagnosticsReport,
    aggregate_evaluation_diagnostics,
    derive_episode_diagnostics,
)
from games.balatro.env.ppo_campaign import (
    CompletedPPOCampaign,
    load_completed_ppo_campaign,
    make_ppo_training_environment,
)
from games.balatro.env.ppo_candidate_evaluation import PPOCandidateIdentity
from games.balatro.env.ppo_contract import PPO_TRAINING_CONTRACT
from games.balatro.env.ppo_promotion import (
    PPOCandidateEvaluationBundle,
    PPOPromotionReport,
    build_ppo_promotion_report,
    execute_fixed_ppo_candidate_evaluation,
    execute_unseeded_ppo_candidate_evaluation,
)
from games.balatro.env.promotion_contract import (
    B0_PROMOTION_CONTRACT_VERSION,
    ZERO_TOLERANCE_PATHOLOGIES,
)
from games.balatro.env.random_baseline import (
    RANDOM_LEGAL_BASELINE_VERSION,
    RandomLegalStrategicBaseline,
)
from games.balatro.env.seeded_evaluation import (
    EVALUATED_BASELINE_VERSIONS,
    FIXED_SEEDED_CORPUS_SHA256,
    FixedSeededEpisodeResult,
    FixedSeededEvaluationReport,
    run_fixed_seeded_evaluation,
)
from games.balatro.env.state import EnvStateFrame, RunStatus
from games.balatro.env.symbolic_baseline import (
    SYMBOLIC_HEADLESS_BASELINE_VERSION,
    DeterministicSymbolicHeadlessBaseline,
    SymbolicHeadlessBaselineError,
)
from games.balatro.env.unseeded_evaluation import (
    UnseededEpisodeResult,
    UnseededEvaluationManifest,
    UnseededEvaluationReport,
    create_unseeded_evaluation_manifest,
    run_unseeded_evaluation,
)
from games.balatro.shop_policy import BalatroShopPolicy


PPO_PROMOTION_EVALUATION_VERSION = "balatro-ppo-promotion-evaluation-v1"
PPO_PROMOTION_PUBLICATION_VERSION = "balatro-ppo-promotion-publication-v1"
SYMBOLIC_PROMOTION_AUTHORITY_VERSION = "balatro-symbolic-promotion-authority-v1"
FINAL_ARTIFACT_NAME = "final.json"


class PPOPromotionEvaluationError(ValueError):
    """Raised when a complete promotion run cannot be executed or verified."""


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise PPOPromotionEvaluationError("promotion artifact is not canonical JSON") from error


def _digest(content: bytes) -> str:
    return sha256(content).hexdigest()


def _canonical_symbolic_decider(
    state: object,
    actions: tuple[BalatroAction, ...],
) -> BalatroAction:
    """Conservative frozen symbolic authority over public strategic candidates."""
    if not actions:
        raise SymbolicHeadlessBaselineError("symbolic promotion authority has no candidates")
    by_name = {action.name: action for action in actions}
    if "SELECT_BLIND" in by_name:
        return by_name["SELECT_BLIND"]
    if "END_SHOP" in by_name:
        candidates = [action for action in actions if action.name != "OPEN_PACK"]
        selected = BalatroShopPolicy().choose_action(state, candidates)
        if selected not in candidates:
            raise SymbolicHeadlessBaselineError(
                "symbolic shop authority returned a noncandidate action"
            )
        return selected
    if "SKIP_PACK" in by_name:
        return by_name["SKIP_PACK"]
    raise SymbolicHeadlessBaselineError(
        "symbolic promotion authority does not own this strategic boundary"
    )


@dataclass(frozen=True)
class BaselineEpisodeEvidence:
    baseline_version: str
    game_seed: str
    policy_seed: str | None
    status: RunStatus
    action_count: int
    frames: tuple[EnvStateFrame, ...]

    def __post_init__(self) -> None:
        if self.baseline_version not in EVALUATED_BASELINE_VERSIONS:
            raise PPOPromotionEvaluationError("baseline evidence version is invalid")
        if not isinstance(self.game_seed, str) or not self.game_seed:
            raise PPOPromotionEvaluationError("baseline evidence game seed is invalid")
        if self.baseline_version == RANDOM_LEGAL_BASELINE_VERSION:
            if not isinstance(self.policy_seed, str) or not self.policy_seed:
                raise PPOPromotionEvaluationError("random baseline policy seed is invalid")
        elif self.policy_seed is not None:
            raise PPOPromotionEvaluationError("symbolic baseline must not have a policy seed")
        if not isinstance(self.status, RunStatus) or not self.status.terminal:
            raise PPOPromotionEvaluationError("baseline evidence is nonterminal")
        if (
            isinstance(self.action_count, bool)
            or not isinstance(self.action_count, int)
            or self.action_count < 1
            or len(self.frames) != self.action_count + 1
        ):
            raise PPOPromotionEvaluationError("baseline evidence action trace is incomplete")
        if self.frames[0].state.phase != "BLIND_SELECT":
            raise PPOPromotionEvaluationError("baseline evidence does not begin at reset")
        if any(frame.status.terminal for frame in self.frames[:-1]):
            raise PPOPromotionEvaluationError("baseline evidence terminates early")
        if self.frames[-1].status is not self.status:
            raise PPOPromotionEvaluationError("baseline evidence terminal status drifted")
        if any(str(frame.info.get("game_seed")) != self.game_seed for frame in self.frames):
            raise PPOPromotionEvaluationError("baseline evidence seed provenance drifted")


def execute_baseline_episode(
    baseline_version: str,
    *,
    game_seed: str,
    policy_seed: str | None,
    environment_factory=make_ppo_training_environment,
    symbolic_decider: Callable[[object, tuple[BalatroAction, ...]], BalatroAction]
    = _canonical_symbolic_decider,
) -> BaselineEpisodeEvidence:
    """Execute one exact baseline episode without truncation or fallback."""
    if baseline_version == RANDOM_LEGAL_BASELINE_VERSION:
        policy = RandomLegalStrategicBaseline(policy_seed)
    elif baseline_version == SYMBOLIC_HEADLESS_BASELINE_VERSION:
        policy = DeterministicSymbolicHeadlessBaseline(symbolic_decider)
    else:
        raise PPOPromotionEvaluationError("unsupported promotion baseline")
    if not callable(environment_factory):
        raise TypeError("environment_factory must be callable")
    environment = environment_factory(0)
    if not isinstance(environment, BalatroHeadlessEnvironment):
        raise TypeError("environment_factory must return BalatroHeadlessEnvironment")
    environment.reset(seed=game_seed)
    if environment.frame.info.get("backend_schema") != PPO_HEADLESS_BACKEND_SCHEMA:
        raise PPOPromotionEvaluationError("baseline backend schema drifted")
    frames = [deepcopy(environment.frame)]
    actions = 0
    for _ in range(PPO_TRAINING_CONTRACT.maximum_episode_actions):
        if environment.frame.status.terminal:
            break
        decision = policy.select(environment.frame, environment.legal_actions())
        if decision is None:
            raise PPOPromotionEvaluationError("baseline returned no nonterminal decision")
        _, _, terminated, truncated, _ = environment.step(decision.action)
        if truncated:
            raise PPOPromotionEvaluationError("baseline evaluation episode truncated")
        if environment.frame.info.get("backend_schema") != PPO_HEADLESS_BACKEND_SCHEMA:
            raise PPOPromotionEvaluationError("baseline backend schema drifted")
        actions += 1
        frames.append(deepcopy(environment.frame))
        if terminated:
            break
    else:
        raise PPOPromotionEvaluationError("baseline episode exceeded the action cap")
    if not environment.frame.status.terminal:
        raise PPOPromotionEvaluationError("baseline episode is incomplete")
    return BaselineEpisodeEvidence(
        baseline_version,
        game_seed,
        policy_seed,
        environment.frame.status,
        actions,
        tuple(frames),
    )


@dataclass(frozen=True)
class BaselineEvaluationBundle:
    source: FixedSeededEvaluationReport | UnseededEvaluationReport
    diagnostics: EvaluationDiagnosticsReport

    def __post_init__(self) -> None:
        if not isinstance(self.source, (FixedSeededEvaluationReport, UnseededEvaluationReport)):
            raise PPOPromotionEvaluationError("baseline bundle source is invalid")
        if not isinstance(self.diagnostics, EvaluationDiagnosticsReport):
            raise PPOPromotionEvaluationError("baseline bundle diagnostics are invalid")
        if self.diagnostics.source_schema_version != self.source.schema_version:
            raise PPOPromotionEvaluationError("baseline bundle source schema drifted")
        if len(self.diagnostics.episodes) != len(self.source.episodes):
            raise PPOPromotionEvaluationError("baseline bundle diagnostics are incomplete")


def execute_fixed_baseline_evaluation(
    *,
    environment_factory=make_ppo_training_environment,
    symbolic_decider=_canonical_symbolic_decider,
) -> BaselineEvaluationBundle:
    evidences: list[BaselineEpisodeEvidence] = []

    def execute(baseline, spec, policy_seed):
        evidence = execute_baseline_episode(
            baseline,
            game_seed=spec.game_seed,
            policy_seed=policy_seed,
            environment_factory=environment_factory,
            symbolic_decider=symbolic_decider,
        )
        evidences.append(evidence)
        return FixedSeededEpisodeResult.completed(
            baseline_version=baseline,
            episode_index=spec.episode_index,
            game_seed=spec.game_seed,
            policy_seed=policy_seed,
            status=evidence.status,
            action_count=evidence.action_count,
        )

    source = run_fixed_seeded_evaluation(execute)
    diagnostics = aggregate_evaluation_diagnostics(
        source,
        tuple(
            derive_episode_diagnostics(result, evidence.frames)
            for result, evidence in zip(source.episodes, evidences, strict=True)
        ),
    )
    return BaselineEvaluationBundle(source, diagnostics)


def execute_unseeded_baseline_evaluation(
    manifest: UnseededEvaluationManifest,
    *,
    environment_factory=make_ppo_training_environment,
    symbolic_decider=_canonical_symbolic_decider,
) -> BaselineEvaluationBundle:
    if not isinstance(manifest, UnseededEvaluationManifest):
        raise TypeError("manifest must be UnseededEvaluationManifest")
    evidences: list[BaselineEpisodeEvidence] = []

    def execute(baseline, spec, policy_seed):
        evidence = execute_baseline_episode(
            baseline,
            game_seed=spec.game_seed,
            policy_seed=policy_seed,
            environment_factory=environment_factory,
            symbolic_decider=symbolic_decider,
        )
        evidences.append(evidence)
        return UnseededEpisodeResult.completed(
            manifest,
            baseline_version=baseline,
            episode_index=spec.episode_index,
            game_seed=spec.game_seed,
            policy_seed=policy_seed,
            status=evidence.status,
            action_count=evidence.action_count,
        )

    source = run_unseeded_evaluation(manifest, execute)
    diagnostics = aggregate_evaluation_diagnostics(
        source,
        tuple(
            derive_episode_diagnostics(result, evidence.frames)
            for result, evidence in zip(source.episodes, evidences, strict=True)
        ),
    )
    return BaselineEvaluationBundle(source, diagnostics)


@dataclass(frozen=True)
class PromotionEvaluationIdentity:
    version: str
    candidate_sha256: str
    promotion_contract_version: str
    fixed_corpus_sha256: str
    manifest_sha256s: tuple[str, ...]
    baseline_versions: tuple[str, ...]
    symbolic_authority_version: str

    def __post_init__(self) -> None:
        if self.version != PPO_PROMOTION_EVALUATION_VERSION:
            raise PPOPromotionEvaluationError("promotion evaluation version mismatch")
        if self.promotion_contract_version != B0_PROMOTION_CONTRACT_VERSION:
            raise PPOPromotionEvaluationError("promotion contract version mismatch")
        if self.fixed_corpus_sha256 != FIXED_SEEDED_CORPUS_SHA256:
            raise PPOPromotionEvaluationError("fixed corpus digest mismatch")
        if self.baseline_versions != EVALUATED_BASELINE_VERSIONS:
            raise PPOPromotionEvaluationError("promotion baseline versions drifted")
        if self.symbolic_authority_version != SYMBOLIC_PROMOTION_AUTHORITY_VERSION:
            raise PPOPromotionEvaluationError("symbolic promotion authority drifted")
        if len(self.manifest_sha256s) != 4 or len(set(self.manifest_sha256s)) != 4:
            raise PPOPromotionEvaluationError("promotion requires four unique manifests")

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["manifest_sha256s"] = list(self.manifest_sha256s)
        value["baseline_versions"] = list(self.baseline_versions)
        return value

    @property
    def sha256(self) -> str:
        return _digest(_canonical_bytes(self.as_dict()))


@dataclass(frozen=True)
class PublishedPromotionEvaluation:
    directory: Path
    evaluation_sha256: str
    candidate_sha256: str
    promotion_report_sha256: str
    promoted: bool
    artifact_sha256s: tuple[tuple[str, str], ...]


def _artifact_payloads(
    identity: PromotionEvaluationIdentity,
    fixed_candidate: PPOCandidateEvaluationBundle,
    fixed_baselines: BaselineEvaluationBundle,
    manifests: tuple[UnseededEvaluationManifest, ...],
    unseeded_candidates: tuple[PPOCandidateEvaluationBundle, ...],
    unseeded_baselines: tuple[BaselineEvaluationBundle, ...],
    report: PPOPromotionReport,
) -> dict[str, bytes]:
    payloads = {
        "run.json": _canonical_bytes({
            "identity": identity.as_dict(),
            "evaluation_sha256": identity.sha256,
        }),
        "fixed-candidate.json": fixed_candidate.source.to_json().encode("utf-8"),
        "fixed-candidate-diagnostics.json": fixed_candidate.diagnostics.to_json().encode("utf-8"),
        "fixed-baselines.json": fixed_baselines.source.to_json().encode("utf-8"),
        "fixed-baseline-diagnostics.json": fixed_baselines.diagnostics.to_json().encode("utf-8"),
        "pathologies.json": _canonical_bytes({name: 0 for name in ZERO_TOLERANCE_PATHOLOGIES}),
        "promotion.json": report.to_json().encode("utf-8"),
    }
    for index, (manifest, candidate, baseline) in enumerate(
        zip(manifests, unseeded_candidates, unseeded_baselines, strict=True)
    ):
        prefix = f"unseeded-{index}"
        payloads[f"{prefix}-manifest.json"] = _canonical_bytes(manifest.as_dict())
        payloads[f"{prefix}-candidate.json"] = candidate.source.to_json().encode("utf-8")
        payloads[f"{prefix}-candidate-diagnostics.json"] = candidate.diagnostics.to_json().encode("utf-8")
        payloads[f"{prefix}-baselines.json"] = baseline.source.to_json().encode("utf-8")
        payloads[f"{prefix}-baseline-diagnostics.json"] = baseline.diagnostics.to_json().encode("utf-8")
    return payloads


def _load_published(directory: Path, candidate_sha256: str) -> PublishedPromotionEvaluation:
    final_path = directory / FINAL_ARTIFACT_NAME
    if not directory.is_dir() or not final_path.is_file():
        raise PPOPromotionEvaluationError("promotion publication is incomplete")
    raw = final_path.read_bytes()
    try:
        final = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PPOPromotionEvaluationError("promotion final artifact is invalid") from error
    if raw != _canonical_bytes(final) or final.get("version") != PPO_PROMOTION_PUBLICATION_VERSION:
        raise PPOPromotionEvaluationError("promotion final artifact is noncanonical")
    if final.get("candidate_sha256") != candidate_sha256:
        raise PPOPromotionEvaluationError("published promotion candidate identity drifted")
    artifacts = final.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise PPOPromotionEvaluationError("promotion artifact index is invalid")
    for name, expected in artifacts.items():
        path = directory / name
        if Path(name).name != name or not path.is_file() or _digest(path.read_bytes()) != expected:
            raise PPOPromotionEvaluationError("published promotion artifact digest mismatch")
    if (
        final.get("promotion_report_sha256") != artifacts.get("promotion.json")
        or not isinstance(final.get("evaluation_sha256"), str)
        or len(final["evaluation_sha256"]) != 64
        or not isinstance(final.get("promoted"), bool)
    ):
        raise PPOPromotionEvaluationError("promotion final linkage is invalid")
    return PublishedPromotionEvaluation(
        directory=directory,
        evaluation_sha256=final["evaluation_sha256"],
        candidate_sha256=candidate_sha256,
        promotion_report_sha256=final["promotion_report_sha256"],
        promoted=final["promoted"],
        artifact_sha256s=tuple(sorted(artifacts.items())),
    )


def execute_and_publish_ppo_promotion(
    campaign: CompletedPPOCampaign,
    output_directory: str | Path,
    *,
    entropy_source=os.urandom,
    environment_factory=make_ppo_training_environment,
    symbolic_decider=_canonical_symbolic_decider,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> PublishedPromotionEvaluation:
    """Execute all 960 episodes, then publish one complete artifact atomically."""
    if not isinstance(campaign, CompletedPPOCampaign):
        raise TypeError("campaign must be CompletedPPOCampaign")
    destination = Path(output_directory).resolve()
    candidate = PPOCandidateIdentity.from_completed_campaign(campaign)
    if destination.exists():
        return _load_published(destination, candidate.sha256)
    if not callable(entropy_source):
        raise TypeError("entropy_source must be callable")
    if progress_callback is not None and not callable(progress_callback):
        raise TypeError("progress_callback must be callable")
    total_arms = 10
    completed_arms = 0

    def progress(stage: str) -> None:
        if progress_callback is not None:
            progress_callback(stage, completed_arms, total_arms)

    progress("creating_manifests")
    manifests = tuple(
        create_unseeded_evaluation_manifest(entropy_source) for _ in range(4)
    )
    identity = PromotionEvaluationIdentity(
        PPO_PROMOTION_EVALUATION_VERSION,
        candidate.sha256,
        B0_PROMOTION_CONTRACT_VERSION,
        FIXED_SEEDED_CORPUS_SHA256,
        tuple(item.manifest_sha256 for item in manifests),
        EVALUATED_BASELINE_VERSIONS,
        SYMBOLIC_PROMOTION_AUTHORITY_VERSION,
    )

    progress("fixed_baselines")
    fixed_baselines = execute_fixed_baseline_evaluation(
        environment_factory=environment_factory,
        symbolic_decider=symbolic_decider,
    )
    completed_arms += 1
    progress("fixed_candidate")
    fixed_candidate = execute_fixed_ppo_candidate_evaluation(
        campaign, environment_factory=environment_factory
    )
    completed_arms += 1
    unseeded_baselines_values = []
    for index, manifest in enumerate(manifests):
        progress(f"unseeded_{index}_baselines")
        unseeded_baselines_values.append(execute_unseeded_baseline_evaluation(
            manifest,
            environment_factory=environment_factory,
            symbolic_decider=symbolic_decider,
        ))
        completed_arms += 1
    unseeded_baselines = tuple(unseeded_baselines_values)
    unseeded_candidate_values = []
    for index, manifest in enumerate(manifests):
        progress(f"unseeded_{index}_candidate")
        unseeded_candidate_values.append(execute_unseeded_ppo_candidate_evaluation(
            campaign, manifest, environment_factory=environment_factory
        ))
        completed_arms += 1
    unseeded_candidates = tuple(unseeded_candidate_values)
    progress("building_report")
    pathology_counts = {name: 0 for name in ZERO_TOLERANCE_PATHOLOGIES}
    report = build_ppo_promotion_report(
        fixed_candidate.diagnostics,
        fixed_baselines.diagnostics,
        tuple(item.diagnostics for item in unseeded_candidates),
        tuple(item.diagnostics for item in unseeded_baselines),
        pathology_counts=pathology_counts,
    )
    payloads = _artifact_payloads(
        identity,
        fixed_candidate,
        fixed_baselines,
        manifests,
        unseeded_candidates,
        unseeded_baselines,
        report,
    )
    artifact_digests = {name: _digest(content) for name, content in payloads.items()}
    final = _canonical_bytes({
        "version": PPO_PROMOTION_PUBLICATION_VERSION,
        "evaluation_sha256": identity.sha256,
        "candidate_sha256": candidate.sha256,
        "promotion_report_sha256": artifact_digests["promotion.json"],
        "promoted": report.promoted,
        "artifacts": artifact_digests,
    })

    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
    try:
        staging.mkdir()
        for name, content in payloads.items():
            (staging / name).write_bytes(content)
        (staging / FINAL_ARTIFACT_NAME).write_bytes(final)
        os.replace(staging, destination)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    progress("complete")
    return _load_published(destination, candidate.sha256)


def run_promotion_cli(artifact_directory: str, output_directory: str) -> PublishedPromotionEvaluation:
    campaign = load_completed_ppo_campaign(artifact_directory)

    def report_progress(stage: str, completed: int, total: int) -> None:
        print(_canonical_bytes({
            "stage": stage,
            "completed_arms": completed,
            "total_arms": total,
        }).decode("utf-8"), flush=True)

    return execute_and_publish_ppo_promotion(
        campaign,
        output_directory,
        progress_callback=report_progress,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Execute and atomically publish the frozen Red/White PPO promotion run."
    )
    parser.add_argument("artifact_directory")
    parser.add_argument("output_directory")
    arguments = parser.parse_args(argv)
    published = run_promotion_cli(
        arguments.artifact_directory,
        arguments.output_directory,
    )
    print(_canonical_bytes({
        "directory": str(published.directory),
        "evaluation_sha256": published.evaluation_sha256,
        "candidate_sha256": published.candidate_sha256,
        "promotion_report_sha256": published.promotion_report_sha256,
        "promoted": published.promoted,
    }).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
