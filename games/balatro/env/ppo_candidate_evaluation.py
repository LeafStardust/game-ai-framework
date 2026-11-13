"""Checkpoint-bound PPO candidate arm for frozen Red/White evaluation."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from typing import Any

from games.balatro.env.action_encoding import (
    ActionMask,
    PUBLIC_ACTION_VERSION,
    action_from_index,
    apply_action_mask,
    legal_action_mask,
)
from games.balatro.env.actions import EnvAction
from games.balatro.env.observation_encoding import (
    EncodedPublicObservation,
    PUBLIC_OBSERVATION_VERSION,
)
from games.balatro.env.ppo_campaign import (
    CompletedPPOCampaign,
    PPO_CAMPAIGN_VERSION,
)
from games.balatro.env.ppo_contract import (
    PPO_POLICY_OUTPUT_SCHEMA,
    PPO_TRAINING_CONTRACT,
    PPOPolicyOutput,
)
from games.balatro.env.promotion_contract import B0_PROMOTION_CONTRACT_VERSION
from games.balatro.env.seeded_evaluation import (
    EVALUATION_DECK,
    EVALUATION_MODE,
    EVALUATION_STAKE,
    FIXED_SEEDED_CORPUS_SHA256,
    FIXED_SEEDED_EPISODES,
    FixedSeededEpisodeSpec,
)
from games.balatro.env.state import RunStatus
from games.balatro.env.unseeded_evaluation import (
    UnseededEpisodeSpec,
    UnseededEvaluationManifest,
)


PPO_CANDIDATE_VERSION = "balatro-red-white-ppo-candidate-v1"
PPO_CANDIDATE_FIXED_REPORT_SCHEMA = "balatro-red-white-ppo-candidate-fixed-v1"
PPO_CANDIDATE_UNSEEDED_REPORT_SCHEMA = "balatro-red-white-ppo-candidate-unseeded-v1"
PPO_CANDIDATE_EPISODE_SCHEMA = "balatro-red-white-ppo-candidate-episode-v1"
PPO_CANDIDATE_POLICY_SEED_SCHEMA = "balatro-red-white-ppo-evaluation-policy-seed-v1"
PPO_CANDIDATE_ACTION_SAMPLE_DOMAIN = "balatro-red-white-ppo-evaluation-action-v1"
FIXED_EVIDENCE_KIND = "FIXED_SEEDED"
UNSEEDED_EVIDENCE_KIND = "UNSEEDED"
_POLICY_SEED_HEX_LENGTH = 16


class PPOCandidateEvaluationError(ValueError):
    """Raised when candidate provenance or evidence is incomplete or drifted."""


def _lower_digest(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PPOCandidateEvaluationError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _exact_nonnegative_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PPOCandidateEvaluationError(f"{name} must be a nonnegative exact integer")
    return value


def _policy_seed(evidence_sha256: str, episode_index: int) -> str:
    digest = _lower_digest(evidence_sha256, "candidate evidence digest")
    index = _exact_nonnegative_int(episode_index, "candidate episode index")
    return sha256(
        f"{PPO_CANDIDATE_POLICY_SEED_SCHEMA}\0{digest}\0{index}".encode("ascii")
    ).hexdigest()[:_POLICY_SEED_HEX_LENGTH].upper()


def _require_policy_seed(value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != _POLICY_SEED_HEX_LENGTH
        or value != value.upper()
    ):
        raise PPOCandidateEvaluationError("candidate policy seed is invalid")
    try:
        int(value, 16)
    except ValueError as error:
        raise PPOCandidateEvaluationError("candidate policy seed is invalid") from error
    return value


@dataclass(frozen=True)
class PPOCandidateIdentity:
    version: str
    campaign_version: str
    promotion_contract_version: str
    training_run_sha256: str
    checkpoint_sha256: str
    progress_sha256: str
    final_sha256: str
    policy_parameter_sha256: str
    completed_batch_count: int
    optimizer_consumed_transitions: int
    observation_version: str
    action_version: str
    deck: str
    stake: str
    mode: str

    def __post_init__(self) -> None:
        if self.version != PPO_CANDIDATE_VERSION:
            raise PPOCandidateEvaluationError("candidate identity version mismatch")
        if self.campaign_version != PPO_CAMPAIGN_VERSION:
            raise PPOCandidateEvaluationError("candidate campaign version mismatch")
        if self.promotion_contract_version != B0_PROMOTION_CONTRACT_VERSION:
            raise PPOCandidateEvaluationError("candidate promotion contract version mismatch")
        for name in (
            "training_run_sha256",
            "checkpoint_sha256",
            "progress_sha256",
            "final_sha256",
            "policy_parameter_sha256",
        ):
            _lower_digest(getattr(self, name), name.replace("_", " "))
        target_batches = (
            PPO_TRAINING_CONTRACT.total_environment_steps
            // PPO_TRAINING_CONTRACT.rollout_batch_size
        )
        if self.completed_batch_count != target_batches:
            raise PPOCandidateEvaluationError("candidate did not complete the frozen schedule")
        if self.optimizer_consumed_transitions != PPO_TRAINING_CONTRACT.total_environment_steps:
            raise PPOCandidateEvaluationError("candidate optimizer transition count drifted")
        if self.observation_version != PUBLIC_OBSERVATION_VERSION:
            raise PPOCandidateEvaluationError("candidate observation version mismatch")
        if self.action_version != PUBLIC_ACTION_VERSION:
            raise PPOCandidateEvaluationError("candidate action version mismatch")
        if (self.deck, self.stake, self.mode) != (
            EVALUATION_DECK,
            EVALUATION_STAKE,
            EVALUATION_MODE,
        ):
            raise PPOCandidateEvaluationError(
                "candidate is not Red Deck / White Stake / normal mode"
            )

    @classmethod
    def from_completed_campaign(
        cls, campaign: CompletedPPOCampaign
    ) -> "PPOCandidateIdentity":
        if not isinstance(campaign, CompletedPPOCampaign):
            raise TypeError("campaign must be CompletedPPOCampaign")
        session = campaign.session
        return cls(
            version=PPO_CANDIDATE_VERSION,
            campaign_version=PPO_CAMPAIGN_VERSION,
            promotion_contract_version=B0_PROMOTION_CONTRACT_VERSION,
            training_run_sha256=campaign.training_run.sha256,
            checkpoint_sha256=campaign.checkpoint_sha256,
            progress_sha256=campaign.progress_sha256,
            final_sha256=campaign.final_sha256,
            policy_parameter_sha256=campaign.policy_parameter_sha256,
            completed_batch_count=session.learner.completed_batch_count,
            optimizer_consumed_transitions=session.optimizer_consumed_transitions,
            observation_version=PUBLIC_OBSERVATION_VERSION,
            action_version=PUBLIC_ACTION_VERSION,
            deck=EVALUATION_DECK,
            stake=EVALUATION_STAKE,
            mode=EVALUATION_MODE,
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))

    @property
    def sha256(self) -> str:
        return sha256(self.to_json().encode("utf-8")).hexdigest()


def fixed_candidate_policy_seed(spec: FixedSeededEpisodeSpec) -> str:
    if (
        not isinstance(spec, FixedSeededEpisodeSpec)
        or spec.episode_index >= len(FIXED_SEEDED_EPISODES)
        or FIXED_SEEDED_EPISODES[spec.episode_index] != spec
    ):
        raise PPOCandidateEvaluationError("candidate fixed episode spec drifted")
    return _policy_seed(FIXED_SEEDED_CORPUS_SHA256, spec.episode_index)


def unseeded_candidate_policy_seed(
    manifest: UnseededEvaluationManifest, spec: UnseededEpisodeSpec
) -> str:
    if not isinstance(manifest, UnseededEvaluationManifest):
        raise TypeError("manifest must be UnseededEvaluationManifest")
    if (
        not isinstance(spec, UnseededEpisodeSpec)
        or spec.episode_index >= len(manifest.episodes)
        or manifest.episodes[spec.episode_index] != spec
    ):
        raise PPOCandidateEvaluationError("candidate unseeded episode spec drifted")
    return _policy_seed(manifest.manifest_sha256, spec.episode_index)


@dataclass(frozen=True)
class PPOCandidateDecision:
    candidate_sha256: str
    policy_seed: str
    decision_index: int
    observation: EncodedPublicObservation
    action_mask: ActionMask
    probabilities: tuple[float, ...]
    value_estimate: float
    action_index: int
    action: EnvAction


def select_ppo_candidate_action(
    identity: PPOCandidateIdentity,
    *,
    policy_seed: str,
    decision_index: int,
    observation: EncodedPublicObservation,
    legal_actions: Iterable[EnvAction],
    policy_output: PPOPolicyOutput,
) -> PPOCandidateDecision:
    """Sample an evaluation action from a stream isolated from training RNG."""

    if not isinstance(identity, PPOCandidateIdentity):
        raise TypeError("identity must be PPOCandidateIdentity")
    seed = _require_policy_seed(policy_seed)
    decision = _exact_nonnegative_int(decision_index, "candidate decision index")
    if (
        not isinstance(observation, EncodedPublicObservation)
        or observation.schema_version != identity.observation_version
    ):
        raise PPOCandidateEvaluationError("candidate observation provenance drifted")
    if not isinstance(policy_output, PPOPolicyOutput):
        raise TypeError("policy_output must be PPOPolicyOutput")
    if (
        policy_output.schema_version != PPO_POLICY_OUTPUT_SCHEMA
        or policy_output.observation_version != identity.observation_version
        or policy_output.action_version != identity.action_version
    ):
        raise PPOCandidateEvaluationError("candidate policy output provenance drifted")
    mask = legal_action_mask(tuple(legal_actions))
    if not any(mask.values):
        raise PPOCandidateEvaluationError("candidate decision has an empty action mask")
    probabilities = apply_action_mask(policy_output.probabilities, mask)
    uniform = int.from_bytes(
        sha256(
            f"{PPO_CANDIDATE_ACTION_SAMPLE_DOMAIN}\0{seed}\0{decision}".encode(
                "ascii"
            )
        ).digest(),
        "big",
    ) / (1 << 256)
    cumulative = 0.0
    selected_index: int | None = None
    for index, probability in enumerate(probabilities):
        cumulative += probability
        if probability > 0.0 and uniform < cumulative:
            selected_index = index
            break
    if selected_index is None or not math.isclose(
        sum(probabilities), 1.0, rel_tol=0.0, abs_tol=1e-12
    ):
        raise PPOCandidateEvaluationError(
            "candidate probabilities could not be sampled exactly"
        )
    return PPOCandidateDecision(
        candidate_sha256=identity.sha256,
        policy_seed=seed,
        decision_index=decision,
        observation=observation,
        action_mask=mask,
        probabilities=probabilities,
        value_estimate=float(policy_output.value_estimate),
        action_index=selected_index,
        action=action_from_index(selected_index),
    )


@dataclass(frozen=True)
class PPOCandidateEpisodeResult:
    schema_version: str
    candidate_sha256: str
    evidence_kind: str
    evidence_sha256: str
    episode_index: int
    game_seed: str
    policy_seed: str
    status: RunStatus
    action_count: int

    def __post_init__(self) -> None:
        if self.schema_version != PPO_CANDIDATE_EPISODE_SCHEMA:
            raise PPOCandidateEvaluationError("candidate episode schema mismatch")
        _lower_digest(self.candidate_sha256, "candidate identity digest")
        if self.evidence_kind not in (FIXED_EVIDENCE_KIND, UNSEEDED_EVIDENCE_KIND):
            raise PPOCandidateEvaluationError("candidate evidence kind is invalid")
        _lower_digest(self.evidence_sha256, "candidate evidence digest")
        _exact_nonnegative_int(self.episode_index, "candidate episode index")
        if not isinstance(self.game_seed, str) or not self.game_seed:
            raise PPOCandidateEvaluationError("candidate game seed is invalid")
        _require_policy_seed(self.policy_seed)
        if not isinstance(self.status, RunStatus) or not self.status.terminal:
            raise PPOCandidateEvaluationError("candidate episode must be terminal")
        _exact_nonnegative_int(self.action_count, "candidate action count")

    @classmethod
    def completed(
        cls,
        identity: PPOCandidateIdentity,
        *,
        evidence_kind: str,
        evidence_sha256: str,
        episode_index: int,
        game_seed: str,
        policy_seed: str,
        status: RunStatus,
        action_count: int,
    ) -> "PPOCandidateEpisodeResult":
        if not isinstance(identity, PPOCandidateIdentity):
            raise TypeError("identity must be PPOCandidateIdentity")
        return cls(
            schema_version=PPO_CANDIDATE_EPISODE_SCHEMA,
            candidate_sha256=identity.sha256,
            evidence_kind=evidence_kind,
            evidence_sha256=evidence_sha256,
            episode_index=episode_index,
            game_seed=game_seed,
            policy_seed=policy_seed,
            status=status,
            action_count=action_count,
        )

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value


@dataclass(frozen=True)
class PPOCandidateFixedReport:
    schema_version: str
    identity: PPOCandidateIdentity
    episodes: tuple[PPOCandidateEpisodeResult, ...]

    def __post_init__(self) -> None:
        if self.schema_version != PPO_CANDIDATE_FIXED_REPORT_SCHEMA:
            raise PPOCandidateEvaluationError("candidate fixed report schema mismatch")
        if not isinstance(self.identity, PPOCandidateIdentity):
            raise PPOCandidateEvaluationError("candidate fixed identity is invalid")
        expected = tuple(
            (
                self.identity.sha256,
                FIXED_EVIDENCE_KIND,
                FIXED_SEEDED_CORPUS_SHA256,
                spec.episode_index,
                spec.game_seed,
                fixed_candidate_policy_seed(spec),
            )
            for spec in FIXED_SEEDED_EPISODES
        )
        actual = tuple(
            (
                episode.candidate_sha256,
                episode.evidence_kind,
                episode.evidence_sha256,
                episode.episode_index,
                episode.game_seed,
                episode.policy_seed,
            )
            for episode in self.episodes
        ) if isinstance(self.episodes, tuple) else ()
        if actual != expected:
            raise PPOCandidateEvaluationError(
                "candidate fixed report is incomplete or out of order"
            )

    @property
    def episode_count(self) -> int:
        return len(self.episodes)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "identity": self.identity.as_dict(),
            "episodes": [episode.as_dict() for episode in self.episodes],
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class PPOCandidateUnseededReport:
    schema_version: str
    identity: PPOCandidateIdentity
    manifest: UnseededEvaluationManifest
    episodes: tuple[PPOCandidateEpisodeResult, ...]

    def __post_init__(self) -> None:
        if self.schema_version != PPO_CANDIDATE_UNSEEDED_REPORT_SCHEMA:
            raise PPOCandidateEvaluationError("candidate unseeded report schema mismatch")
        if not isinstance(self.identity, PPOCandidateIdentity):
            raise PPOCandidateEvaluationError("candidate unseeded identity is invalid")
        if not isinstance(self.manifest, UnseededEvaluationManifest):
            raise PPOCandidateEvaluationError("candidate unseeded manifest is invalid")
        expected = tuple(
            (
                self.identity.sha256,
                UNSEEDED_EVIDENCE_KIND,
                self.manifest.manifest_sha256,
                spec.episode_index,
                spec.game_seed,
                unseeded_candidate_policy_seed(self.manifest, spec),
            )
            for spec in self.manifest.episodes
        )
        actual = tuple(
            (
                episode.candidate_sha256,
                episode.evidence_kind,
                episode.evidence_sha256,
                episode.episode_index,
                episode.game_seed,
                episode.policy_seed,
            )
            for episode in self.episodes
        ) if isinstance(self.episodes, tuple) else ()
        if actual != expected:
            raise PPOCandidateEvaluationError(
                "candidate unseeded report is incomplete or out of order"
            )

    @property
    def episode_count(self) -> int:
        return len(self.episodes)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "identity": self.identity.as_dict(),
            "manifest": self.manifest.as_dict(),
            "episodes": [episode.as_dict() for episode in self.episodes],
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


FixedCandidateExecutor = Callable[
    [PPOCandidateIdentity, FixedSeededEpisodeSpec, str],
    PPOCandidateEpisodeResult,
]
UnseededCandidateExecutor = Callable[
    [PPOCandidateIdentity, UnseededEpisodeSpec, str],
    PPOCandidateEpisodeResult,
]


def run_fixed_ppo_candidate_evaluation(
    identity: PPOCandidateIdentity,
    execute_episode: FixedCandidateExecutor,
) -> PPOCandidateFixedReport:
    if not isinstance(identity, PPOCandidateIdentity):
        raise TypeError("identity must be PPOCandidateIdentity")
    if not callable(execute_episode):
        raise TypeError("candidate episode executor must be callable")
    results = tuple(
        execute_episode(identity, spec, fixed_candidate_policy_seed(spec))
        for spec in FIXED_SEEDED_EPISODES
    )
    if any(not isinstance(result, PPOCandidateEpisodeResult) for result in results):
        raise TypeError("candidate executor must return PPOCandidateEpisodeResult")
    return PPOCandidateFixedReport(
        schema_version=PPO_CANDIDATE_FIXED_REPORT_SCHEMA,
        identity=identity,
        episodes=results,
    )


def run_unseeded_ppo_candidate_evaluation(
    identity: PPOCandidateIdentity,
    manifest: UnseededEvaluationManifest,
    execute_episode: UnseededCandidateExecutor,
) -> PPOCandidateUnseededReport:
    if not isinstance(identity, PPOCandidateIdentity):
        raise TypeError("identity must be PPOCandidateIdentity")
    if not isinstance(manifest, UnseededEvaluationManifest):
        raise TypeError("manifest must be UnseededEvaluationManifest")
    if not callable(execute_episode):
        raise TypeError("candidate episode executor must be callable")
    results = tuple(
        execute_episode(
            identity,
            spec,
            unseeded_candidate_policy_seed(manifest, spec),
        )
        for spec in manifest.episodes
    )
    if any(not isinstance(result, PPOCandidateEpisodeResult) for result in results):
        raise TypeError("candidate executor must return PPOCandidateEpisodeResult")
    return PPOCandidateUnseededReport(
        schema_version=PPO_CANDIDATE_UNSEEDED_REPORT_SCHEMA,
        identity=identity,
        manifest=manifest,
        episodes=results,
    )
