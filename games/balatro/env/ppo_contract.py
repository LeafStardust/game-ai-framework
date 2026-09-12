"""Frozen PPO configuration and deterministic rollout evidence boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from numbers import Real
from typing import Any, Iterable, Sequence

from games.balatro.env.action_encoding import (
    PUBLIC_ACTION_SCHEMA,
    PUBLIC_ACTION_VERSION,
    ActionMask,
    action_from_index,
    apply_action_mask,
    legal_action_mask,
)
from games.balatro.env.actions import EnvAction
from games.balatro.env.observation_encoding import (
    PUBLIC_OBSERVATION_SCHEMA,
    PUBLIC_OBSERVATION_VERSION,
    EncodedPublicObservation,
)
from games.balatro.env.promotion_contract import B0_PROMOTION_CONTRACT_VERSION
from games.balatro.env.seeded_evaluation import (
    EVALUATION_DECK,
    EVALUATION_MODE,
    EVALUATION_STAKE,
    FIXED_SEEDED_EPISODES,
)
from games.balatro.env.state import EnvStateFrame, RunStatus, TurnOwner


PPO_TRAINING_CONTRACT_VERSION = "balatro-red-white-ppo-training-v1"
PPO_TRAINING_RUN_SCHEMA = "balatro-red-white-ppo-run-v1"
PPO_POLICY_OUTPUT_SCHEMA = "balatro-red-white-ppo-policy-output-v1"
PPO_ROLLOUT_EPISODE_SCHEMA = "balatro-red-white-ppo-rollout-episode-v1"
PPO_ALGORITHM = "clipped_ppo"
PPO_REWARD_CONTRACT = "canonical_backend_reward_only"
PPO_TRAINING_SEED_POLICY = "derived_non_holdout_game_seeds"


class PPOContractError(ValueError):
    """Raised when PPO configuration or rollout evidence is not exact."""


def _exact_int(value: object, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise PPOContractError(f"{name} must be an exact integer of at least {minimum}")
    return value


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise PPOContractError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise PPOContractError(f"{name} must be finite")
    return result


def _lower_hex(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PPOContractError(f"{name} must be 32 bytes of lowercase hex")
    return value


@dataclass(frozen=True)
class PPOTrainingContract:
    version: str = PPO_TRAINING_CONTRACT_VERSION
    algorithm: str = PPO_ALGORITHM
    observation_version: str = PUBLIC_OBSERVATION_VERSION
    observation_size: int = len(PUBLIC_OBSERVATION_SCHEMA.feature_names)
    action_version: str = PUBLIC_ACTION_VERSION
    action_size: int = len(PUBLIC_ACTION_SCHEMA.slots)
    promotion_contract_version: str = B0_PROMOTION_CONTRACT_VERSION
    reward_contract: str = PPO_REWARD_CONTRACT
    training_seed_policy: str = PPO_TRAINING_SEED_POLICY
    policy_hidden_sizes: tuple[int, ...] = (512, 256)
    activation: str = "tanh"
    parallel_environments: int = 8
    rollout_steps_per_environment: int = 256
    minibatch_size: int = 256
    update_epochs: int = 10
    total_environment_steps: int = 2_097_152
    discount_factor: float = 0.99
    gae_lambda: float = 0.95
    policy_clip: float = 0.20
    value_clip: float = 0.20
    learning_rate: float = 0.0003
    entropy_coefficient: float = 0.01
    value_coefficient: float = 0.50
    maximum_gradient_norm: float = 0.50
    maximum_episode_actions: int = 4096

    def __post_init__(self) -> None:
        # Keep v1 pre-registration immutable. A changed design requires a new version.
        frozen = {
            "version": PPO_TRAINING_CONTRACT_VERSION,
            "algorithm": PPO_ALGORITHM,
            "observation_version": PUBLIC_OBSERVATION_VERSION,
            "observation_size": len(PUBLIC_OBSERVATION_SCHEMA.feature_names),
            "action_version": PUBLIC_ACTION_VERSION,
            "action_size": len(PUBLIC_ACTION_SCHEMA.slots),
            "promotion_contract_version": B0_PROMOTION_CONTRACT_VERSION,
            "reward_contract": PPO_REWARD_CONTRACT,
            "training_seed_policy": PPO_TRAINING_SEED_POLICY,
            "policy_hidden_sizes": (512, 256),
            "activation": "tanh",
            "parallel_environments": 8,
            "rollout_steps_per_environment": 256,
            "minibatch_size": 256,
            "update_epochs": 10,
            "total_environment_steps": 2_097_152,
            "discount_factor": 0.99,
            "gae_lambda": 0.95,
            "policy_clip": 0.20,
            "value_clip": 0.20,
            "learning_rate": 0.0003,
            "entropy_coefficient": 0.01,
            "value_coefficient": 0.50,
            "maximum_gradient_norm": 0.50,
            "maximum_episode_actions": 4096,
        }
        if asdict(self) != frozen:
            raise PPOContractError("PPO training contract v1 has drifted")
        batch_size = self.parallel_environments * self.rollout_steps_per_environment
        if batch_size % self.minibatch_size or self.total_environment_steps % batch_size:
            raise PPOContractError("PPO batch schedule must divide exactly")

    @property
    def rollout_batch_size(self) -> int:
        return self.parallel_environments * self.rollout_steps_per_environment

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["policy_hidden_sizes"] = list(self.policy_hidden_sizes)
        value["rollout_batch_size"] = self.rollout_batch_size
        return value

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))

    @property
    def sha256(self) -> str:
        return sha256(self.to_json().encode("utf-8")).hexdigest()


PPO_TRAINING_CONTRACT = PPOTrainingContract()


def _derived_seed(root_seed_hex: str, kind: str) -> str:
    return sha256(
        f"{PPO_TRAINING_RUN_SCHEMA}\0{root_seed_hex}\0{kind}".encode("ascii")
    ).hexdigest()


@dataclass(frozen=True)
class PPOTrainingRun:
    schema_version: str
    contract_sha256: str
    root_seed_hex: str
    learner_seed_hex: str
    rollout_seed_hex: str

    def __post_init__(self) -> None:
        if self.schema_version != PPO_TRAINING_RUN_SCHEMA:
            raise PPOContractError("PPO training run schema version mismatch")
        if self.contract_sha256 != PPO_TRAINING_CONTRACT.sha256:
            raise PPOContractError("PPO training contract digest mismatch")
        root = _lower_hex(self.root_seed_hex, "root seed")
        _lower_hex(self.learner_seed_hex, "learner seed")
        _lower_hex(self.rollout_seed_hex, "rollout seed")
        if self.learner_seed_hex != _derived_seed(root, "learner"):
            raise PPOContractError("learner seed provenance mismatch")
        if self.rollout_seed_hex != _derived_seed(root, "rollout"):
            raise PPOContractError("rollout seed provenance mismatch")
        if self.learner_seed_hex == self.rollout_seed_hex:
            raise PPOContractError("learner and rollout seed streams must be separate")

    @classmethod
    def from_seed(cls, seed: str | int) -> "PPOTrainingRun":
        if isinstance(seed, bool) or not isinstance(seed, (str, int)):
            raise TypeError("PPO root seed must be a string or exact integer")
        root = sha256(
            f"{PPO_TRAINING_RUN_SCHEMA}\0root\0{seed}".encode("utf-8")
        ).hexdigest()
        return cls(
            schema_version=PPO_TRAINING_RUN_SCHEMA,
            contract_sha256=PPO_TRAINING_CONTRACT.sha256,
            root_seed_hex=root,
            learner_seed_hex=_derived_seed(root, "learner"),
            rollout_seed_hex=_derived_seed(root, "rollout"),
        )

    def game_seed(self, episode_index: int) -> str:
        index = _exact_int(episode_index, "training episode index")
        result = sha256(
            f"{PPO_TRAINING_RUN_SCHEMA}\0{self.rollout_seed_hex}\0game\0{index}".encode(
                "ascii"
            )
        ).hexdigest()[:8].upper()
        if result in {spec.game_seed for spec in FIXED_SEEDED_EPISODES}:
            raise PPOContractError("derived training seed collides with fixed evaluation corpus")
        return result

    def as_dict(self) -> dict[str, str]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))

    @property
    def sha256(self) -> str:
        return sha256(self.to_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PPOPolicyOutput:
    schema_version: str
    observation_version: str
    action_version: str
    probabilities: tuple[float, ...]
    value_estimate: float

    def __post_init__(self) -> None:
        if self.schema_version != PPO_POLICY_OUTPUT_SCHEMA:
            raise PPOContractError("PPO policy output schema version mismatch")
        if self.observation_version != PUBLIC_OBSERVATION_VERSION:
            raise PPOContractError("PPO policy observation version mismatch")
        if self.action_version != PUBLIC_ACTION_VERSION:
            raise PPOContractError("PPO policy action version mismatch")
        if not isinstance(self.probabilities, tuple) or len(self.probabilities) != len(
            PUBLIC_ACTION_SCHEMA.slots
        ):
            raise PPOContractError("PPO policy output shape does not match action schema")
        for value in self.probabilities:
            number = _finite_number(value, "PPO policy probability")
            if number < 0.0:
                raise PPOContractError("PPO policy probabilities must be nonnegative")
        _finite_number(self.value_estimate, "PPO policy value estimate")


@dataclass(frozen=True)
class PPORolloutDecision:
    training_run_sha256: str
    episode_index: int
    decision_index: int
    observation: EncodedPublicObservation
    action_mask: ActionMask
    probabilities: tuple[float, ...]
    value_estimate: float
    action_index: int
    action: EnvAction

    def __post_init__(self) -> None:
        _lower_hex(self.training_run_sha256, "training run digest")
        _exact_int(self.episode_index, "rollout episode index")
        _exact_int(self.decision_index, "rollout decision index")
        if (
            not isinstance(self.observation, EncodedPublicObservation)
            or self.observation.schema_version != PUBLIC_OBSERVATION_VERSION
            or self.observation.shape != PUBLIC_OBSERVATION_SCHEMA.shape
        ):
            raise PPOContractError("rollout observation schema mismatch")
        if (
            not isinstance(self.action_mask, ActionMask)
            or self.action_mask.schema_version != PUBLIC_ACTION_VERSION
            or self.action_mask.shape != PUBLIC_ACTION_SCHEMA.shape
        ):
            raise PPOContractError("rollout action mask schema mismatch")
        if not any(self.action_mask.values):
            raise PPOContractError("nonterminal PPO decision has an empty legal action mask")
        if not isinstance(self.probabilities, tuple) or len(self.probabilities) != len(
            self.action_mask.values
        ):
            raise PPOContractError("rollout probability shape mismatch")
        total = 0.0
        for probability, allowed in zip(
            self.probabilities, self.action_mask.values, strict=True
        ):
            number = _finite_number(probability, "rollout probability")
            if number < 0.0 or (not allowed and number != 0.0):
                raise PPOContractError("rollout probabilities violate the canonical mask")
            total += number
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise PPOContractError("rollout probabilities must sum to one")
        _finite_number(self.value_estimate, "rollout value estimate")
        index = _exact_int(self.action_index, "rollout action index")
        if index >= len(self.action_mask.values) or not self.action_mask.values[index]:
            raise PPOContractError("rollout sampled an illegal action")
        if self.probabilities[index] <= 0.0:
            raise PPOContractError("rollout sampled a zero-probability action")
        if self.action != action_from_index(index):
            raise PPOContractError("rollout action does not match its canonical index")

    def as_dict(self) -> dict[str, Any]:
        return {
            "training_run_sha256": self.training_run_sha256,
            "episode_index": self.episode_index,
            "decision_index": self.decision_index,
            "observation": {
                "schema_version": self.observation.schema_version,
                "values": list(self.observation.values),
            },
            "action_mask": {
                "schema_version": self.action_mask.schema_version,
                "values": list(self.action_mask.values),
            },
            "probabilities": list(self.probabilities),
            "value_estimate": self.value_estimate,
            "action_index": self.action_index,
            "action": {
                "alias": self.action.alias,
                "params": [list(item) for item in self.action.params],
            },
        }


def select_ppo_action(
    training_run: PPOTrainingRun,
    *,
    episode_index: int,
    decision_index: int,
    observation: EncodedPublicObservation,
    legal_actions: Iterable[EnvAction],
    policy_output: PPOPolicyOutput,
) -> PPORolloutDecision:
    """Apply canonical legality and sample from the isolated rollout stream."""
    if not isinstance(training_run, PPOTrainingRun):
        raise TypeError("training_run must be PPOTrainingRun")
    if not isinstance(policy_output, PPOPolicyOutput):
        raise TypeError("policy_output must be PPOPolicyOutput")
    if (
        not isinstance(observation, EncodedPublicObservation)
        or observation.schema_version != policy_output.observation_version
    ):
        raise PPOContractError("policy output does not match the rollout observation")
    episode = _exact_int(episode_index, "rollout episode index")
    decision = _exact_int(decision_index, "rollout decision index")
    mask = legal_action_mask(legal_actions)
    if not any(mask.values):
        raise PPOContractError("nonterminal PPO decision has an empty legal action mask")
    probabilities = apply_action_mask(policy_output.probabilities, mask)
    digest = sha256(
        (
            f"{PPO_ROLLOUT_EPISODE_SCHEMA}\0{training_run.rollout_seed_hex}\0"
            f"{episode}\0{decision}"
        ).encode("ascii")
    ).digest()
    uniform = int.from_bytes(digest, "big") / (1 << 256)
    cumulative = 0.0
    selected_index: int | None = None
    for index, probability in enumerate(probabilities):
        cumulative += probability
        if probability > 0.0 and uniform < cumulative:
            selected_index = index
            break
    if selected_index is None:
        raise PPOContractError("normalized PPO probabilities could not be sampled exactly")
    return PPORolloutDecision(
        training_run_sha256=training_run.sha256,
        episode_index=episode,
        decision_index=decision,
        observation=observation,
        action_mask=mask,
        probabilities=probabilities,
        value_estimate=float(policy_output.value_estimate),
        action_index=selected_index,
        action=action_from_index(selected_index),
    )


@dataclass(frozen=True)
class PPORolloutBoundary:
    observation: EncodedPublicObservation
    deck: str
    stake: str
    mode: str
    phase: str
    status: RunStatus
    owner: TurnOwner
    ante: int
    money: int
    score: float
    blind_requirement: float | None

    @classmethod
    def from_frame(cls, frame: EnvStateFrame) -> "PPORolloutBoundary":
        if not isinstance(frame, EnvStateFrame):
            raise TypeError("rollout boundary requires EnvStateFrame")
        state = frame.state
        requirement = None if state.blind is None else _finite_number(
            state.blind.requirement, "rollout blind requirement"
        )
        return cls(
            observation=frame.encoded_observation(),
            deck=state.deck_name,
            stake=state.stake_name,
            mode=EVALUATION_MODE,
            phase=state.phase,
            status=frame.status,
            owner=frame.owner,
            ante=_exact_int(state.ante, "rollout Ante", minimum=1),
            money=_exact_int(state.money, "rollout money", minimum=-10**9),
            score=_finite_number(state.score, "rollout score"),
            blind_requirement=requirement,
        )

    def __post_init__(self) -> None:
        if (
            not isinstance(self.observation, EncodedPublicObservation)
            or self.observation.schema_version != PUBLIC_OBSERVATION_VERSION
            or self.observation.shape != PUBLIC_OBSERVATION_SCHEMA.shape
        ):
            raise PPOContractError("rollout boundary observation schema mismatch")
        if (self.deck, self.stake, self.mode) != (
            EVALUATION_DECK,
            EVALUATION_STAKE,
            EVALUATION_MODE,
        ):
            raise PPOContractError("rollout boundary is not Red Deck / White Stake / normal mode")
        if not isinstance(self.phase, str) or not self.phase:
            raise PPOContractError("rollout boundary phase is invalid")
        if not isinstance(self.status, RunStatus) or not isinstance(self.owner, TurnOwner):
            raise PPOContractError("rollout boundary status/owner is invalid")
        _exact_int(self.ante, "rollout Ante", minimum=1)
        _exact_int(self.money, "rollout money", minimum=-10**9)
        _finite_number(self.score, "rollout score")
        if self.blind_requirement is not None:
            requirement = _finite_number(
                self.blind_requirement, "rollout blind requirement"
            )
            if requirement <= 0.0:
                raise PPOContractError("rollout blind requirement must be positive")

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation": {
                "schema_version": self.observation.schema_version,
                "values": list(self.observation.values),
            },
            "deck": self.deck,
            "stake": self.stake,
            "mode": self.mode,
            "phase": self.phase,
            "status": self.status.value,
            "owner": self.owner.value,
            "ante": self.ante,
            "money": self.money,
            "score": self.score,
            "blind_requirement": self.blind_requirement,
        }


@dataclass(frozen=True)
class PPORolloutEpisode:
    schema_version: str
    training_run: PPOTrainingRun
    episode_index: int
    game_seed: str
    boundaries: tuple[PPORolloutBoundary, ...]
    decisions: tuple[PPORolloutDecision, ...]
    rewards: tuple[float, ...]
    truncated: bool = False

    def __post_init__(self) -> None:
        if self.schema_version != PPO_ROLLOUT_EPISODE_SCHEMA:
            raise PPOContractError("PPO rollout episode schema version mismatch")
        if not isinstance(self.training_run, PPOTrainingRun):
            raise PPOContractError("PPO rollout training run is invalid")
        index = _exact_int(self.episode_index, "rollout episode index")
        if self.game_seed != self.training_run.game_seed(index):
            raise PPOContractError("PPO rollout game seed provenance mismatch")
        if self.truncated is not False:
            raise PPOContractError("truncated PPO rollouts are incomplete")
        if (
            not isinstance(self.boundaries, tuple)
            or not isinstance(self.decisions, tuple)
            or not isinstance(self.rewards, tuple)
            or len(self.boundaries) != len(self.decisions) + 1
            or len(self.rewards) != len(self.decisions)
            or not self.decisions
        ):
            raise PPOContractError("PPO rollout must contain one complete transition sequence")
        if len(self.decisions) > PPO_TRAINING_CONTRACT.maximum_episode_actions:
            raise PPOContractError("PPO rollout exceeds the frozen episode action cap")
        if any(not isinstance(item, PPORolloutBoundary) for item in self.boundaries):
            raise PPOContractError("PPO rollout contains an invalid boundary")
        if any(not isinstance(item, PPORolloutDecision) for item in self.decisions):
            raise PPOContractError("PPO rollout contains an invalid decision")
        first, final = self.boundaries[0], self.boundaries[-1]
        if (
            first.phase != "BLIND_SELECT"
            or first.ante != 1
            or first.status is not RunStatus.RUNNING
        ):
            raise PPOContractError("PPO rollout must begin at the Ante-1 blind-select reset")
        if any(
            boundary.status is not RunStatus.RUNNING
            or boundary.owner is not TurnOwner.AGENT
            for boundary in self.boundaries[:-1]
        ):
            raise PPOContractError("PPO decision boundaries must be running and agent-owned")
        if not final.status.terminal or final.owner is not TurnOwner.TERMINAL:
            raise PPOContractError("PPO rollout must end at one complete terminal boundary")
        if any(
            after.ante < before.ante
            for before, after in zip(self.boundaries, self.boundaries[1:], strict=False)
        ):
            raise PPOContractError("PPO rollout Ante progression cannot decrease")
        if final.blind_requirement is None:
            raise PPOContractError("PPO terminal boundary has no blind requirement")
        if final.status is RunStatus.LOSS and final.score >= final.blind_requirement:
            raise PPOContractError("PPO terminal loss already satisfies its blind requirement")
        if final.status is RunStatus.ANTE_8_WIN and (
            final.ante < 8 or final.score < final.blind_requirement
        ):
            raise PPOContractError("PPO Ante 8 win contradicts its terminal boundary")
        for decision_index, (boundary, decision) in enumerate(
            zip(self.boundaries, self.decisions, strict=False)
        ):
            if (
                decision.training_run_sha256 != self.training_run.sha256
                or decision.episode_index != index
                or decision.decision_index != decision_index
                or decision.observation != boundary.observation
            ):
                raise PPOContractError("PPO rollout decision provenance drifted")
        for reward in self.rewards:
            _finite_number(reward, "PPO rollout reward")

    @classmethod
    def completed(
        cls,
        training_run: PPOTrainingRun,
        *,
        episode_index: int,
        frames: Sequence[EnvStateFrame],
        decisions: Sequence[PPORolloutDecision],
        rewards: Sequence[float],
        truncated: bool = False,
    ) -> "PPORolloutEpisode":
        index = _exact_int(episode_index, "rollout episode index")
        return cls(
            schema_version=PPO_ROLLOUT_EPISODE_SCHEMA,
            training_run=training_run,
            episode_index=index,
            game_seed=training_run.game_seed(index),
            boundaries=tuple(PPORolloutBoundary.from_frame(frame) for frame in frames),
            decisions=tuple(decisions),
            rewards=tuple(rewards),
            truncated=truncated,
        )

    @property
    def action_count(self) -> int:
        return len(self.decisions)

    @property
    def status(self) -> RunStatus:
        return self.boundaries[-1].status

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "training_run": self.training_run.as_dict(),
            "episode_index": self.episode_index,
            "game_seed": self.game_seed,
            "boundaries": [boundary.as_dict() for boundary in self.boundaries],
            "decisions": [decision.as_dict() for decision in self.decisions],
            "rewards": list(self.rewards),
            "truncated": self.truncated,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
