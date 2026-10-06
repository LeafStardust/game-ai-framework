"""Fixed-state cost attribution for the production PPO tactical authority."""

from __future__ import annotations

import argparse
import copy as copy_module
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Callable

import games.balatro.state as balatro_state
from games.balatro.env.blind_progression import activate_selected_blind_progression
from games.balatro.env.episode_backend import pristine_red_white_reset
from games.balatro.env.ppo_campaign import (
    _atomic_write,
    make_ppo_training_environment,
)
from games.balatro.env.ppo_contract import (
    PPO_TRAINING_CONTRACT,
    PPOContractError,
    PPOTrainingRun,
)
from games.balatro.env.ppo_learner import PPOLearner
from games.balatro.env.ppo_rollout import collect_complete_ppo_episode
from games.balatro.env.parity import canonical_public_state_signature
from games.balatro.env.public_observation import public_observation_state
from games.balatro.env.select_blind import select_blind_exact
from games.balatro.live.generated_consumable_outcomes import (
    LiveGeneratedConsumableScoreOutcomeModel,
)
from games.balatro.live.post_hand_outcomes import LiveVisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


PPO_TACTICAL_COST_SCHEMA = "balatro-red-white-ppo-tactical-cost-v1"
PPO_TACTICAL_COST_WORKLOAD = "red-white-ppo-first-episode-first-small-blind-decision-v1"
PPO_TACTICAL_EPISODE_COST_SCHEMA = "balatro-red-white-ppo-tactical-episode-cost-v1"
PPO_TACTICAL_CANDIDATE_SUBOWNER_SCHEMA = (
    "balatro-red-white-ppo-tactical-candidate-subowner-v15"
)
PPO_TACTICAL_INERT_ALIAS_SCHEMA = "balatro-red-white-ppo-inert-alias-v1"
PPO_TACTICAL_SCHEDULE_PROBE_SCHEMA = "balatro-red-white-ppo-schedule-probe-v1"
PPO_TACTICAL_HORIZON_TWO_PARITY_SCHEMA = (
    "balatro-red-white-ppo-horizon-two-parity-v2"
)
PPO_TACTICAL_EPISODE_PAIRED_PARITY_SCHEMA = (
    "balatro-red-white-ppo-episode-paired-parity-v2"
)
PPO_TACTICAL_SELECTIVE_ESCALATION_SCHEMA = (
    "balatro-red-white-ppo-selective-escalation-v1"
)
_RECONSTRUCT_TYPE_SAMPLE_LIMIT = 100_000
_STATE_CARD_SAMPLE_LIMIT = 100_000
_SELECTIVE_ESCALATION_TARGET_DIGEST = (
    "a63e3298ce4b73019dc17a6e3f6dbe9f42babdb22acfbc508c3626b51699c2c2"
)

_EPISODE_7_EXPECTED_PREFIX = (
    ("4a0542854bbb2308d64a0d3dbed557c81d846fe314ecbfe78b0bc253dc847ff2", "PLAY_CARDS", (0, 1, 2, 3), ((2, 18, 2000, False),)),
    ("19f3c1857846f11b54219c9879bca59e62985ba615d1090d2d0f5cefac7f6fc2", "PLAY_CARDS", (0, 1), ((2, 18, 2000, False),)),
    ("142d9f84e3dffefcae262869bf45c528512d07485ad5dd65a9e68a36e2683e49", "PLAY_CARDS", (0, 1, 6, 7), ((2, 15, 2000, False),)),
    ("ccdaf04a97754f506cfadf4766b192b1a3e863708c3cf1f9c7bd4fee08426372", "PLAY_CARDS", (0, 1, 2, 3, 4), ((2, 3, 2000, False),)),
    ("b24654edbeefb4c3ae62d391a5f1a8d109055d4621f3f0185b1f3a26323e9fda", "DISCARD_CARDS", (0, 1, 4, 5, 6), ((2, 18, 2000, False),)),
    ("bf661a1b04e2c84019e55d4e2716abc3450a8956ff666e787f6a42c3465ccd0c", "DISCARD_CARDS", (2, 3, 4, 6, 7), ((2, 18, 2000, False),)),
    ("e7e679b56595ebab6691b3723f3a85b2747dbbcd06f7ed9fb5be84df003e01c9", "PLAY_CARDS", (0, 1, 2, 3, 5), ((2, 15, 2000, False),)),
    ("7ba8ed02c8b736e7222f85fc0726d35711465a4519f6e7850a36a92e9d020784", "PLAY_CARDS", (3, 4), ((2, 18, 2000, False),)),
    ("a63e3298ce4b73019dc17a6e3f6dbe9f42babdb22acfbc508c3626b51699c2c2", "DISCARD_CARDS", (0, 3, 4, 5, 6), ((2, 18, 2000, False), (3, 51, 2000, False), (3, 51, 1000, False))),
    ("a9794ce7394796bc117fb3c635a487cc04f9288746a2beaba8f4158f2406579f", "PLAY_CARDS", (0, 1, 4, 5), ((2, 3, 2000, False),)),
    ("85496a49e6df7095bf3f9ef59d6132d9e309e5ba8ac769f7b5e86f470163bc7a", "DISCARD_CARDS", (0, 2, 3, 6, 7), ((2, 292, 2000, False),)),
    ("f63c5da42cd96a7e9ecd9281dee0dd90666edf8722f618ee5857fddf8301a145", "DISCARD_CARDS", (0, 2, 3, 6, 7), ((2, 292, 2000, False),)),
)

_EPISODE_43_DECISION_11_EXPECTED_PREFIX = (
    ("9b05ad7b121cfa68ee3870890210234afed26eeefca478d53ba3c98bb519740b", "DISCARD_CARDS", (1, 2, 3, 4, 5), ((2, 18, 2000, False),)),
    ("123361c9c6c172fbeee19a9a1c038c0a68d0a5af3ea0696897cb6807b8c35375", "PLAY_CARDS", (3, 4, 6, 7), ((2, 15, 2000, False),)),
    ("dc7a9792a1acba6882424d32fb53ecf0824fecf5cdf3d26bf5470f725e5b9d43", "PLAY_CARDS", (3, 4, 5, 6), ((2, 18, 2000, False),)),
    ("65910dc05a14c25115968d573167adcaef514535f96ce28c7e3464e3b887e315", "PLAY_CARDS", (0, 2, 3, 4, 5), ((2, 2, 2000, False),)),
    ("10aa3ec7d205f66ec794e2bf2d1ee1e8ce51841ccaa3d5ed2a08973ac7366956", "DISCARD_CARDS", (2, 3, 4, 5, 7), ((2, 18, 2000, False),)),
    ("f58101a2d56ab973970e54334a3ae65d521d4b10c4f11a0e8e858ea51954e458", "DISCARD_CARDS", (2, 3, 4, 5, 6), ((2, 18, 2000, False),)),
    ("cad063dfe9d997a77f21edf808879c296761586f2bf9563d7bf200c0b7b47ed4", "PLAY_CARDS", (1, 3, 4, 5, 6), ((2, 17, 2000, False),)),
    ("62ffa82b488e08cd4eec8f9086a7463307dafabe7fc6baf35141cda127ddf33f", "PLAY_CARDS", (4, 5, 6, 7), ((2, 18, 2000, False),)),
    ("9599c0c7b3cc5fa75f6c2f7f2cd7241de33cc9f035a9c81ed1d02f292e14ddb6", "PLAY_CARDS", (2, 3, 5, 6), ((2, 3, 2000, False),)),
    ("ca2f82b95d9abdce25ab8645de280a6d66ac83de241da63a99b14bd9ffb1914f", "DISCARD_CARDS", (2, 3, 4, 5, 6), ((2, 108, 2000, False),)),
    ("5134dd7a7dda282a67b196c8aefc95615600a0aa7b4400903448706f36563b52", "PLAY_CARDS", (1, 2, 3, 5, 6), ((2, 164, 2000, False), (2, 97, 1000, False))),
    ("7fb297b6f491b1618c66c449c74d1bbb184559af6f9f8b99a55601758c07a21d", "DISCARD_CARDS", (5,), ((2, 252, 2000, False), (3, 2000, 2000, True))),
)

_CANDIDATE_HELPER_NAMES = (
    "_root_play_candidates",
    "_guaranteed_sun_action",
    "_child_play_candidates",
    "_child_discard_candidates",
    "_diverse_play_beam",
    "_diverse_discard_beam",
    "_projection_free_discard_reserve",
    "_discard_priority",
    "_evaluator_evaluate",
    "_evaluator_context",
    "_evaluator_discard_value",
    "_evaluator_estimate_play",
    "_evaluator_guaranteed_clear",
    "_evaluator_retained_structure",
    "_evaluator_hand_for_cards",
    "_score_outcomes_project",
    "_score_outcomes_project_transition",
    "_score_outcomes_hook_transition",
    "_score_outcomes_non_hook_transition",
    "_generated_consumable_project_transition",
    "_generated_joker_projector_score",
    "_visible_card_project_transition",
    "_state_copy_for_tactical_projection",
    "_state_projection_deepcopy",
    "_state_deepcopy_reconstruct",
    "_state_deepcopy_dict",
    "_state_deepcopy_list",
    "_score_outcomes_scorer_score",
    "_generate_play_actions",
)


@dataclass(frozen=True)
class PPOTacticalCostReport:
    schema: str
    workload: str
    root_seed: str
    game_seed: str
    action: str
    selected_hand_indices: tuple[int, ...]
    search_attempts: tuple[tuple[int, int, int, bool], ...]
    total_elapsed_seconds: float
    candidate_generation_elapsed_seconds: float
    search_evaluation_elapsed_seconds: float
    policy_arbitration_elapsed_seconds: float
    other_elapsed_seconds: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True)


@dataclass(frozen=True)
class PPOTacticalEpisodeDecisionCost:
    public_input_sha256: str
    action: str
    selected_hand_indices: tuple[int, ...]
    search_attempts: tuple[tuple[int, int, int, bool], ...]
    total_elapsed_seconds: float
    candidate_generation_elapsed_seconds: float
    search_evaluation_elapsed_seconds: float
    policy_arbitration_elapsed_seconds: float
    other_elapsed_seconds: float


@dataclass(frozen=True)
class PPOTacticalEpisodeCostReport:
    schema: str
    root_seed: str
    episode_index: int
    stream_index: int
    game_seed: str
    environment_transitions: int
    total_elapsed_seconds: float
    tactical_elapsed_seconds: float
    decisions: tuple[PPOTacticalEpisodeDecisionCost, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True)


def write_ppo_tactical_episode_report(
    path: str | Path,
    report: PPOTacticalEpisodeCostReport,
) -> str:
    """Atomically publish one complete tactical episode trace."""
    if not isinstance(report, PPOTacticalEpisodeCostReport):
        raise TypeError("report must be PPOTacticalEpisodeCostReport")
    destination = Path(path)
    if not destination.parent.is_dir():
        raise PPOContractError("PPO tactical report directory does not exist")
    content = report.to_json().encode("utf-8")
    _atomic_write(destination, content)
    return sha256(content).hexdigest()


@dataclass(frozen=True)
class PPOTacticalScheduleProbeResult:
    max_horizon: int
    max_nodes: int
    action: str
    selected_hand_indices: tuple[int, ...]
    search_attempts: tuple[tuple[int, int, int, bool], ...]
    elapsed_seconds: float


@dataclass(frozen=True)
class PPOTacticalScheduleProbeReport:
    schema: str
    root_seed: str
    game_seed: str
    verified_prefix_decisions: int
    public_input_sha256: str
    results: tuple[PPOTacticalScheduleProbeResult, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True)


@dataclass(frozen=True)
class PPOTacticalDecisionSignal:
    mode: str
    confidence: float
    setup_discard_consensus: bool
    clear_path_candidates: int
    best_play_pace_ratio: float
    selected_pace_ratio: float | None
    selected_fallback_value: float | None


@dataclass(frozen=True)
class PPOTacticalHorizonTwoParityRecord:
    public_input_sha256: str
    expected_action: str
    expected_hand_indices: tuple[int, ...]
    action: str
    selected_hand_indices: tuple[int, ...]
    search_attempts: tuple[tuple[int, int, int, bool], ...]
    elapsed_seconds: float
    matches_expected: bool
    probe_signal: PPOTacticalDecisionSignal
    production_signal: PPOTacticalDecisionSignal | None


@dataclass(frozen=True)
class PPOTacticalHorizonTwoParityReport:
    schema: str
    root_seed: str
    game_seed: str
    verified_production_decisions: int
    all_actions_match: bool
    records: tuple[PPOTacticalHorizonTwoParityRecord, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True)


@dataclass(frozen=True)
class PPOTacticalEpisodePairedParityRecord:
    public_input_sha256: str
    production_action: str
    production_hand_indices: tuple[int, ...]
    production_search_attempts: tuple[tuple[int, int, int, bool], ...]
    production_elapsed_seconds: float
    probe_action: str
    probe_hand_indices: tuple[int, ...]
    probe_search_attempts: tuple[tuple[int, int, int, bool], ...]
    probe_elapsed_seconds: float
    matches_production: bool
    probe_signal: PPOTacticalDecisionSignal
    production_signal: PPOTacticalDecisionSignal


@dataclass(frozen=True)
class PPOTacticalEpisodePairedParityReport:
    schema: str
    root_seed: str
    episode_index: int
    game_seed: str
    environment_transitions: int
    all_actions_match: bool
    records: tuple[PPOTacticalEpisodePairedParityRecord, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True)


@dataclass(frozen=True)
class PPOTacticalSelectiveEscalationRecord:
    decision_index: int
    public_input_sha256: str
    shallow_action: str
    shallow_hand_indices: tuple[int, ...]
    shallow_signal: PPOTacticalDecisionSignal
    triggered: bool
    escalated_action: str | None
    escalated_hand_indices: tuple[int, ...] | None
    escalated_search_attempts: tuple[tuple[int, int, int, bool], ...] | None
    production_action: str
    production_hand_indices: tuple[int, ...]
    matches_production: bool


@dataclass(frozen=True)
class PPOTacticalSelectiveEscalationReport:
    schema: str
    root_seed: str
    episode_index: int
    game_seed: str
    verified_production_decisions: int
    trigger_count: int
    all_escalations_match: bool
    records: tuple[PPOTacticalSelectiveEscalationRecord, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True)


@dataclass(frozen=True)
class PPOTacticalCandidateHelperCost:
    name: str
    calls: int
    exclusive_elapsed_seconds: float


@dataclass(frozen=True)
class PPOTacticalInertAliasReport:
    schema: str
    public_input_sha256: str
    selected_hand_indices: tuple[int, ...]
    inherited_public_state_sha256: str
    wrapped_public_state_sha256: str
    inherited_input_card_aliases: int
    wrapped_input_card_aliases: int


def _state_card_ids(state) -> set[int]:
    return {
        id(card)
        for collection in (
            getattr(state, "deck", ()),
            getattr(state, "owned_deck", ()) or (),
            getattr(state, "hand", ()),
            getattr(state, "discard_pile", ()),
        )
        for card in collection
    }


def compare_first_production_inert_transition_aliases(
    *, root_seed: str = "RED-WHITE-PPO-V1"
) -> PPOTacticalInertAliasReport:
    training_run = PPOTrainingRun.from_seed(root_seed)
    run = pristine_red_white_reset(training_run.game_seed(0))
    run = activate_selected_blind_progression(run)
    run = select_blind_exact(run)
    state = public_observation_state(run.public)
    environment = make_ppo_training_environment(0)
    evaluator = environment._backend._tactical_decision_engine.planner.evaluator
    action = evaluator.action_generator.generate_play_actions(state)[0]
    hand = evaluator._hand_for_cards(state, action.cards)
    model = evaluator.score_outcomes

    inherited = super(
        LiveGeneratedConsumableScoreOutcomeModel, model
    ).project_transition(hand, state, action.cards)
    wrapped = LiveGeneratedConsumableScoreOutcomeModel.project_transition(
        model, hand, state, action.cards
    )
    inherited_state = inherited.state_after_scoring
    wrapped_state = wrapped.state_after_scoring
    input_ids = _state_card_ids(state)
    inherited_signature = canonical_public_state_signature(inherited_state)
    wrapped_signature = canonical_public_state_signature(wrapped_state)
    return PPOTacticalInertAliasReport(
        schema=PPO_TACTICAL_INERT_ALIAS_SCHEMA,
        public_input_sha256=_public_input_sha256(state),
        selected_hand_indices=tuple(state.hand.index(card) for card in action.cards),
        inherited_public_state_sha256=sha256(
            json.dumps(inherited_signature, separators=(",", ":")).encode("ascii")
        ).hexdigest(),
        wrapped_public_state_sha256=sha256(
            json.dumps(wrapped_signature, separators=(",", ":")).encode("ascii")
        ).hexdigest(),
        inherited_input_card_aliases=len(input_ids & _state_card_ids(inherited_state)),
        wrapped_input_card_aliases=len(input_ids & _state_card_ids(wrapped_state)),
    )


@dataclass(frozen=True)
class PPOTacticalCandidateReconstructTypeSample:
    type_name: str
    sampled_calls: int
    exclusive_elapsed_seconds: float


@dataclass(frozen=True)
class PPOTacticalCandidateSubownerReport:
    schema: str
    root_seed: str
    episode_index: int
    stream_index: int
    game_seed: str
    verified_prefix_decisions: int
    target_decision_index: int
    public_input_sha256: str
    action: str
    selected_hand_indices: tuple[int, ...]
    search_attempts: tuple[tuple[int, int, int, bool], ...]
    evaluation_cache_hits: int
    evaluation_cache_misses: int
    generated_consumable_transition_calls: int
    generated_consumable_inert_calls: int
    generated_consumable_eight_ball_capable_calls: int
    generated_consumable_main_generator_capable_calls: int
    generated_consumable_sixth_sense_capable_calls: int
    total_elapsed_seconds: float
    candidate_generation_elapsed_seconds: float
    helper_costs: tuple[PPOTacticalCandidateHelperCost, ...]
    reconstruct_type_sample_limit: int
    reconstruct_type_sampled_calls: int
    reconstruct_type_samples: tuple[PPOTacticalCandidateReconstructTypeSample, ...]
    state_card_sample_limit: int
    state_card_validation_sampled_calls: int
    state_card_validation_elapsed_seconds: float
    state_card_shallow_copy_sampled_calls: int
    state_card_shallow_copy_elapsed_seconds: float
    residual_candidate_elapsed_seconds: float

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True)


def write_ppo_tactical_candidate_subowner_report(
    path: str | Path,
    report: PPOTacticalCandidateSubownerReport,
) -> str:
    """Atomically publish one complete tactical candidate-subowner trace."""
    if not isinstance(report, PPOTacticalCandidateSubownerReport):
        raise TypeError("report must be PPOTacticalCandidateSubownerReport")
    destination = Path(path)
    if not destination.parent.is_dir():
        raise PPOContractError("PPO tactical report directory does not exist")
    content = report.to_json().encode("utf-8")
    _atomic_write(destination, content)
    return sha256(content).hexdigest()


@dataclass
class _CostAccumulator:
    candidate_generation: float = 0.0
    ranked_search: float = 0.0
    policy_arbitration: float = 0.0


@dataclass
class _ExclusiveHelperAccumulator:
    clock: Callable[[], float]
    enabled: bool = False
    calls: dict[str, int] = field(default_factory=dict)
    elapsed: dict[str, float] = field(default_factory=dict)
    stack: list[list[object]] = field(default_factory=list)

    def wrap(self, name: str, function):
        def timed(*args, **kwargs):
            if not self.enabled:
                return function(*args, **kwargs)
            frame: list[object] = [name, float(self.clock()), 0.0]
            self.stack.append(frame)
            try:
                return function(*args, **kwargs)
            finally:
                total = max(0.0, float(self.clock()) - float(frame[1]))
                if not self.stack or self.stack.pop() is not frame:
                    raise RuntimeError("candidate helper timing stack drifted")
                exclusive = max(0.0, total - float(frame[2]))
                self.calls[name] = self.calls.get(name, 0) + 1
                self.elapsed[name] = self.elapsed.get(name, 0.0) + exclusive
                if self.stack:
                    self.stack[-1][2] = float(self.stack[-1][2]) + total

        return timed


@dataclass
class _ReconstructTypeSampler:
    clock: Callable[[], float]
    limit: int
    sampled_calls: int = 0
    calls_by_type: dict[type, int] = field(default_factory=dict)
    elapsed_by_type: dict[type, float] = field(default_factory=dict)
    stack: list[list[object]] = field(default_factory=list)

    @property
    def active(self) -> bool:
        return self.sampled_calls < self.limit or bool(self.stack)

    def wrap_reconstruct(self, function):
        def sampled(value, *args, **kwargs):
            if not self.active:
                return function(value, *args, **kwargs)
            value_type = type(value)
            record = self.sampled_calls < self.limit
            if record:
                self.sampled_calls += 1
                self.calls_by_type[value_type] = (
                    self.calls_by_type.get(value_type, 0) + 1
                )
            frame: list[object] = [
                value_type if record else None,
                float(self.clock()),
                0.0,
            ]
            self.stack.append(frame)
            try:
                return function(value, *args, **kwargs)
            finally:
                total = max(0.0, float(self.clock()) - float(frame[1]))
                if not self.stack or self.stack.pop() is not frame:
                    raise RuntimeError("reconstruction type timing stack drifted")
                if record:
                    exclusive = max(0.0, total - float(frame[2]))
                    self.elapsed_by_type[value_type] = (
                        self.elapsed_by_type.get(value_type, 0.0) + exclusive
                    )
                if self.stack:
                    self.stack[-1][2] = float(self.stack[-1][2]) + total

        return sampled

    def wrap_child(self, function):
        def sampled(*args, **kwargs):
            if not self.stack:
                return function(*args, **kwargs)
            frame: list[object] = [None, float(self.clock()), 0.0]
            self.stack.append(frame)
            try:
                return function(*args, **kwargs)
            finally:
                total = max(0.0, float(self.clock()) - float(frame[1]))
                if not self.stack or self.stack.pop() is not frame:
                    raise RuntimeError("reconstruction child timing stack drifted")
                self.stack[-1][2] = float(self.stack[-1][2]) + total

        return sampled


class _TargetDecisionReached(Exception):
    def __init__(self, report: PPOTacticalCandidateSubownerReport):
        super().__init__("target tactical decision reached")
        self.report = report


class _ScheduleProbeReached(Exception):
    def __init__(self, report: PPOTacticalScheduleProbeReport):
        super().__init__("target tactical schedule probe reached")
        self.report = report


class _HorizonTwoParityReached(Exception):
    def __init__(self, report: PPOTacticalHorizonTwoParityReport):
        super().__init__("episode-seven horizon-two parity target reached")
        self.report = report


class _SelectiveEscalationReached(Exception):
    def __init__(self, report: PPOTacticalSelectiveEscalationReport):
        super().__init__("episode-seven selective-escalation target reached")
        self.report = report


def _decision_signal(decision) -> PPOTacticalDecisionSignal:
    optional_values = (
        decision.selected_pace_ratio,
        decision.selected_fallback_value,
    )
    values = (
        decision.confidence,
        decision.best_play_pace_ratio,
        *(value for value in optional_values if value is not None),
    )
    if any(not math.isfinite(float(value)) for value in values):
        raise RuntimeError("tactical decision signal contains a nonfinite value")
    return PPOTacticalDecisionSignal(
        mode=str(decision.mode),
        confidence=float(decision.confidence),
        setup_discard_consensus=bool(decision.setup_discard_consensus),
        clear_path_candidates=int(decision.clear_path_candidates),
        best_play_pace_ratio=float(decision.best_play_pace_ratio),
        selected_pace_ratio=(
            None
            if decision.selected_pace_ratio is None
            else float(decision.selected_pace_ratio)
        ),
        selected_fallback_value=(
            None
            if decision.selected_fallback_value is None
            else float(decision.selected_fallback_value)
        ),
    )


def probe_episode_seven_selective_escalation(
    *,
    root_seed: str = "RED-WHITE-PPO-V1",
) -> PPOTacticalSelectiveEscalationReport:
    if root_seed != "RED-WHITE-PPO-V1":
        raise PPOContractError(
            "selective-escalation probe requires root seed RED-WHITE-PPO-V1"
        )

    episode_index = 7
    target_index = next(
        index
        for index, expected in enumerate(_EPISODE_7_EXPECTED_PREFIX)
        if expected[0] == _SELECTIVE_ESCALATION_TARGET_DIGEST
    )
    training_run = PPOTrainingRun.from_seed(root_seed)
    environment = make_ppo_training_environment(episode_index)
    shallow_environment = make_ppo_training_environment(episode_index)
    escalation_environment = make_ppo_training_environment(episode_index)
    learner = PPOLearner(training_run)
    engine = environment._backend._tactical_decision_engine
    shallow_engine = shallow_environment._backend._tactical_decision_engine
    escalation_engine = escalation_environment._backend._tactical_decision_engine
    original_decide = engine.decide
    original_limits = (
        shallow_engine.max_horizon,
        shallow_engine.max_search_nodes,
        escalation_engine.max_horizon,
        escalation_engine.max_search_nodes,
    )
    shallow_engine.max_horizon = 2
    shallow_engine.max_search_nodes = 2000
    escalation_engine.max_horizon = 3
    escalation_engine.max_search_nodes = 2000
    records: list[PPOTacticalSelectiveEscalationRecord] = []

    def attempt_tuples(decision):
        return tuple(
            (
                attempt.horizon,
                attempt.nodes_evaluated,
                attempt.max_nodes,
                attempt.budget_exceeded,
            )
            for attempt in decision.search_attempts
        )

    def decide(state):
        decision_index = len(records)
        if decision_index > target_index:
            raise PPOContractError("selective-escalation probe exceeded target")
        expected = _EPISODE_7_EXPECTED_PREFIX[decision_index]
        digest = _public_input_sha256(state)
        if digest != expected[0]:
            raise PPOContractError(
                f"selective-escalation digest drifted at decision {decision_index}"
            )

        shallow_decision = shallow_engine.decide(state)
        shallow_indices = tuple(
            state.hand.index(card) for card in shallow_decision.action.cards
        )
        triggered = shallow_engine._selective_deepening_candidate(shallow_decision)
        if triggered != (decision_index == target_index):
            raise PPOContractError(
                f"selective-escalation trigger drifted at decision {decision_index}"
            )
        if _public_input_sha256(state) != digest:
            raise RuntimeError("selective-escalation shallow probe mutated state")

        escalated_decision = escalation_engine.decide(state) if triggered else None
        escalated_indices = (
            tuple(state.hand.index(card) for card in escalated_decision.action.cards)
            if escalated_decision is not None
            else None
        )
        if _public_input_sha256(state) != digest:
            raise RuntimeError("selective-escalation deep probe mutated state")

        production_decision = original_decide(state)
        production_indices = tuple(
            state.hand.index(card) for card in production_decision.action.cards
        )
        production_result = (
            production_decision.action.name,
            production_indices,
            attempt_tuples(production_decision),
        )
        if production_result != expected[1:]:
            raise PPOContractError(
                f"selective-escalation production drifted at decision {decision_index}"
            )
        matches = (
            escalated_decision is not None
            and (escalated_decision.action.name, escalated_indices)
            == (production_decision.action.name, production_indices)
        )
        records.append(
            PPOTacticalSelectiveEscalationRecord(
                decision_index=decision_index,
                public_input_sha256=digest,
                shallow_action=shallow_decision.action.name,
                shallow_hand_indices=shallow_indices,
                shallow_signal=_decision_signal(shallow_decision),
                triggered=triggered,
                escalated_action=(
                    escalated_decision.action.name
                    if escalated_decision is not None
                    else None
                ),
                escalated_hand_indices=escalated_indices,
                escalated_search_attempts=(
                    attempt_tuples(escalated_decision)
                    if escalated_decision is not None
                    else None
                ),
                production_action=production_decision.action.name,
                production_hand_indices=production_indices,
                matches_production=matches,
            )
        )
        if decision_index == target_index:
            if not matches:
                raise PPOContractError(
                    "selective escalation did not recover production action"
                )
            raise _SelectiveEscalationReached(
                PPOTacticalSelectiveEscalationReport(
                    schema=PPO_TACTICAL_SELECTIVE_ESCALATION_SCHEMA,
                    root_seed=root_seed,
                    episode_index=episode_index,
                    game_seed=training_run.game_seed(episode_index),
                    verified_production_decisions=len(records),
                    trigger_count=sum(record.triggered for record in records),
                    all_escalations_match=all(
                        record.matches_production
                        for record in records
                        if record.triggered
                    ),
                    records=tuple(records),
                )
            )
        return production_decision

    engine.decide = decide
    try:
        collect_complete_ppo_episode(
            environment,
            training_run,
            episode_index=episode_index,
            policy=learner.model.infer,
        )
    except _SelectiveEscalationReached as reached:
        return reached.report
    finally:
        (
            shallow_engine.max_horizon,
            shallow_engine.max_search_nodes,
            escalation_engine.max_horizon,
            escalation_engine.max_search_nodes,
        ) = original_limits
    raise PPOContractError("episode-seven selective-escalation target was not reached")


def probe_episode_seven_horizon_two_parity(
    *,
    root_seed: str = "RED-WHITE-PPO-V1",
    clock: Callable[[], float] = perf_counter,
) -> PPOTacticalHorizonTwoParityReport:
    if root_seed != "RED-WHITE-PPO-V1":
        raise PPOContractError("horizon-two parity requires root seed RED-WHITE-PPO-V1")
    if not callable(clock):
        raise TypeError("clock must be callable")

    episode_index = 7
    target_index = len(_EPISODE_7_EXPECTED_PREFIX) - 1
    training_run = PPOTrainingRun.from_seed(root_seed)
    environment = make_ppo_training_environment(episode_index)
    probe_environment = make_ppo_training_environment(episode_index)
    learner = PPOLearner(training_run)
    engine = environment._backend._tactical_decision_engine
    probe_engine = probe_environment._backend._tactical_decision_engine
    original_decide = engine.decide
    original_probe_horizon = probe_engine.max_horizon
    original_probe_nodes = probe_engine.max_search_nodes
    probe_engine.max_horizon = 2
    probe_engine.max_search_nodes = 2000
    verified = {"count": 0}
    records: list[PPOTacticalHorizonTwoParityRecord] = []

    def decide(state):
        decision_index = len(records)
        expected = _EPISODE_7_EXPECTED_PREFIX[decision_index]
        digest = _public_input_sha256(state)
        if digest != expected[0]:
            raise PPOContractError(
                f"horizon-two parity digest drifted at decision {decision_index}"
            )
        started = float(clock())
        probe_decision = probe_engine.decide(state)
        elapsed = max(0.0, float(clock()) - started)
        action = probe_decision.action.name
        indices = tuple(state.hand.index(card) for card in probe_decision.action.cards)
        matches = (action, indices) == expected[1:3]
        probe_signal = _decision_signal(probe_decision)
        probe_attempts = tuple(
            (
                attempt.horizon,
                attempt.nodes_evaluated,
                attempt.max_nodes,
                attempt.budget_exceeded,
            )
            for attempt in probe_decision.search_attempts
        )
        if _public_input_sha256(state) != digest:
            raise RuntimeError("horizon-two parity mutated the production state")
        if decision_index == target_index:
            records.append(
                PPOTacticalHorizonTwoParityRecord(
                    public_input_sha256=digest,
                    expected_action=expected[1],
                    expected_hand_indices=expected[2],
                    action=action,
                    selected_hand_indices=indices,
                    search_attempts=probe_attempts,
                    elapsed_seconds=elapsed,
                    matches_expected=matches,
                    probe_signal=probe_signal,
                    production_signal=None,
                )
            )
            raise _HorizonTwoParityReached(
                PPOTacticalHorizonTwoParityReport(
                    schema=PPO_TACTICAL_HORIZON_TWO_PARITY_SCHEMA,
                    root_seed=root_seed,
                    game_seed=training_run.game_seed(episode_index),
                    verified_production_decisions=verified["count"],
                    all_actions_match=all(record.matches_expected for record in records),
                    records=tuple(records),
                )
            )

        production_decision = original_decide(state)
        production_action = production_decision.action.name
        production_indices = tuple(
            state.hand.index(card) for card in production_decision.action.cards
        )
        production_attempts = tuple(
            (
                attempt.horizon,
                attempt.nodes_evaluated,
                attempt.max_nodes,
                attempt.budget_exceeded,
            )
            for attempt in production_decision.search_attempts
        )
        if (production_action, production_indices, production_attempts) != expected[1:]:
            raise PPOContractError(
                f"horizon-two parity production drifted at decision {decision_index}"
            )
        records.append(
            PPOTacticalHorizonTwoParityRecord(
                public_input_sha256=digest,
                expected_action=expected[1],
                expected_hand_indices=expected[2],
                action=action,
                selected_hand_indices=indices,
                search_attempts=probe_attempts,
                elapsed_seconds=elapsed,
                matches_expected=matches,
                probe_signal=probe_signal,
                production_signal=_decision_signal(production_decision),
            )
        )
        verified["count"] += 1
        return production_decision

    engine.decide = decide
    try:
        collect_complete_ppo_episode(
            environment,
            training_run,
            episode_index=episode_index,
            policy=learner.model.infer,
        )
    except _HorizonTwoParityReached as reached:
        return reached.report
    finally:
        probe_engine.max_horizon = original_probe_horizon
        probe_engine.max_search_nodes = original_probe_nodes
    raise PPOContractError("episode-seven horizon-two parity target was not reached")


def probe_episode_zero_horizon_two_parity(
    *,
    root_seed: str = "RED-WHITE-PPO-V1",
    clock: Callable[[], float] = perf_counter,
) -> PPOTacticalEpisodePairedParityReport:
    if root_seed != "RED-WHITE-PPO-V1":
        raise PPOContractError("episode-zero parity requires root seed RED-WHITE-PPO-V1")
    if not callable(clock):
        raise TypeError("clock must be callable")

    episode_index = 0
    training_run = PPOTrainingRun.from_seed(root_seed)
    environment = make_ppo_training_environment(episode_index)
    probe_environment = make_ppo_training_environment(episode_index)
    learner = PPOLearner(training_run)
    engine = environment._backend._tactical_decision_engine
    probe_engine = probe_environment._backend._tactical_decision_engine
    original_decide = engine.decide
    original_probe_horizon = probe_engine.max_horizon
    original_probe_nodes = probe_engine.max_search_nodes
    probe_engine.max_horizon = 2
    probe_engine.max_search_nodes = 2000
    records: list[PPOTacticalEpisodePairedParityRecord] = []

    def attempt_tuples(decision):
        return tuple(
            (
                attempt.horizon,
                attempt.nodes_evaluated,
                attempt.max_nodes,
                attempt.budget_exceeded,
            )
            for attempt in decision.search_attempts
        )

    def decide(state):
        digest = _public_input_sha256(state)
        probe_started = float(clock())
        probe_decision = probe_engine.decide(state)
        probe_elapsed = max(0.0, float(clock()) - probe_started)
        if _public_input_sha256(state) != digest:
            raise RuntimeError("episode-zero parity probe mutated production state")

        production_started = float(clock())
        production_decision = original_decide(state)
        production_elapsed = max(0.0, float(clock()) - production_started)
        production_indices = tuple(
            state.hand.index(card) for card in production_decision.action.cards
        )
        probe_indices = tuple(
            state.hand.index(card) for card in probe_decision.action.cards
        )
        records.append(
            PPOTacticalEpisodePairedParityRecord(
                public_input_sha256=digest,
                production_action=production_decision.action.name,
                production_hand_indices=production_indices,
                production_search_attempts=attempt_tuples(production_decision),
                production_elapsed_seconds=production_elapsed,
                probe_action=probe_decision.action.name,
                probe_hand_indices=probe_indices,
                probe_search_attempts=attempt_tuples(probe_decision),
                probe_elapsed_seconds=probe_elapsed,
                matches_production=(
                    probe_decision.action.name,
                    probe_indices,
                )
                == (production_decision.action.name, production_indices),
                probe_signal=_decision_signal(probe_decision),
                production_signal=_decision_signal(production_decision),
            )
        )
        return production_decision

    engine.decide = decide
    try:
        episode = collect_complete_ppo_episode(
            environment,
            training_run,
            episode_index=episode_index,
            policy=learner.model.infer,
        )
    finally:
        probe_engine.max_horizon = original_probe_horizon
        probe_engine.max_search_nodes = original_probe_nodes
    if episode.episode_index != episode_index:
        raise RuntimeError("episode-zero parity episode index drifted")
    return PPOTacticalEpisodePairedParityReport(
        schema=PPO_TACTICAL_EPISODE_PAIRED_PARITY_SCHEMA,
        root_seed=root_seed,
        episode_index=episode_index,
        game_seed=training_run.game_seed(episode_index),
        environment_transitions=len(episode.decisions),
        all_actions_match=all(record.matches_production for record in records),
        records=tuple(records),
    )


def probe_episode_seven_bounded_schedules(
    *,
    root_seed: str = "RED-WHITE-PPO-V1",
    clock: Callable[[], float] = perf_counter,
) -> PPOTacticalScheduleProbeReport:
    if root_seed != "RED-WHITE-PPO-V1":
        raise PPOContractError("schedule probe requires root seed RED-WHITE-PPO-V1")
    if not callable(clock):
        raise TypeError("clock must be callable")

    episode_index = 7
    target_index = len(_EPISODE_7_EXPECTED_PREFIX) - 1
    training_run = PPOTrainingRun.from_seed(root_seed)
    environment = make_ppo_training_environment(episode_index)
    learner = PPOLearner(training_run)
    engine = environment._backend._tactical_decision_engine
    original_decide = engine.decide
    original_horizon = engine.max_horizon
    original_nodes = engine.max_search_nodes
    verified = {"count": 0}

    def decide(state):
        decision_index = verified["count"]
        expected = _EPISODE_7_EXPECTED_PREFIX[decision_index]
        digest = _public_input_sha256(state)
        if digest != expected[0]:
            raise PPOContractError(
                f"schedule probe digest drifted at decision {decision_index}"
            )
        if decision_index < target_index:
            decision = original_decide(state)
            action = decision.action.name
            indices = tuple(state.hand.index(card) for card in decision.action.cards)
            attempts = tuple(
                (a.horizon, a.nodes_evaluated, a.max_nodes, a.budget_exceeded)
                for a in decision.search_attempts
            )
            if (action, indices, attempts) != expected[1:]:
                raise PPOContractError(
                    f"schedule probe prefix drifted at decision {decision_index}"
                )
            verified["count"] += 1
            return decision

        results = []
        for max_horizon in (2, 3):
            engine.max_horizon = max_horizon
            engine.max_search_nodes = 2000
            started = float(clock())
            decision = original_decide(state)
            elapsed = max(0.0, float(clock()) - started)
            results.append(
                PPOTacticalScheduleProbeResult(
                    max_horizon=max_horizon,
                    max_nodes=2000,
                    action=decision.action.name,
                    selected_hand_indices=tuple(
                        state.hand.index(card) for card in decision.action.cards
                    ),
                    search_attempts=tuple(
                        (
                            attempt.horizon,
                            attempt.nodes_evaluated,
                            attempt.max_nodes,
                            attempt.budget_exceeded,
                        )
                        for attempt in decision.search_attempts
                    ),
                    elapsed_seconds=elapsed,
                )
            )
            if _public_input_sha256(state) != digest:
                raise RuntimeError("schedule probe mutated the frozen target state")
        raise _ScheduleProbeReached(
            PPOTacticalScheduleProbeReport(
                schema=PPO_TACTICAL_SCHEDULE_PROBE_SCHEMA,
                root_seed=root_seed,
                game_seed=training_run.game_seed(episode_index),
                verified_prefix_decisions=verified["count"],
                public_input_sha256=digest,
                results=tuple(results),
            )
        )

    engine.decide = decide
    try:
        collect_complete_ppo_episode(
            environment,
            training_run,
            episode_index=episode_index,
            policy=learner.model.infer,
        )
    except _ScheduleProbeReached as reached:
        return reached.report
    finally:
        engine.max_horizon = original_horizon
        engine.max_search_nodes = original_nodes
    raise PPOContractError("episode-seven schedule-probe target was not reached")


def _timed_call(clock, accumulator: _CostAccumulator, field: str, function):
    def timed(*args, **kwargs):
        started = float(clock())
        try:
            return function(*args, **kwargs)
        finally:
            setattr(
                accumulator,
                field,
                getattr(accumulator, field) + float(clock()) - started,
            )

    return timed


def _instrument_planner(planner, clock, accumulator: _CostAccumulator) -> None:
    planner._candidate_actions = _timed_call(
        clock,
        accumulator,
        "candidate_generation",
        planner._candidate_actions,
    )


def _public_input_sha256(state) -> str:
    signature = canonical_public_state_signature(state)
    content = json.dumps(signature, separators=(",", ":"), ensure_ascii=True)
    return sha256(content.encode("ascii")).hexdigest()


def _generated_consumable_capabilities(model, state) -> tuple[bool, bool, bool]:
    eight_ball = model._activation_count(state, "EightBallJoker") > 0
    main_generator = bool(model._effective_main_abilities(state))
    sixth_sense = any(
        type(joker).__name__ == "SixthSenseJoker" and model._joker_active(joker)
        for joker in getattr(state, "jokers", []) or []
    )
    return eight_ball, main_generator, sixth_sense


def _instrument_episode_engine(engine, clock, records) -> None:
    active = {"cost": None}

    def timed(field, function):
        def wrapped(*args, **kwargs):
            accumulator = active["cost"]
            if accumulator is None:
                return function(*args, **kwargs)
            started = float(clock())
            try:
                return function(*args, **kwargs)
            finally:
                setattr(
                    accumulator,
                    field,
                    getattr(accumulator, field) + float(clock()) - started,
                )

        return wrapped

    def instrument_planner(planner):
        planner._candidate_actions = timed(
            "candidate_generation",
            planner._candidate_actions,
        )

    instrument_planner(engine.planner)
    original_adaptive_planner = engine._adaptive_planner

    def adaptive_planner(config):
        planner = original_adaptive_planner(config)
        instrument_planner(planner)
        return planner

    engine._adaptive_planner = adaptive_planner
    engine.rank_plans = timed("ranked_search", engine.rank_plans)
    engine.policy.decide = timed("policy_arbitration", engine.policy.decide)
    original_decide = engine.decide

    def decide(state):
        accumulator = _CostAccumulator()
        active["cost"] = accumulator
        started = float(clock())
        try:
            decision = original_decide(state)
        finally:
            total = float(clock()) - started
            active["cost"] = None

        search_evaluation = max(
            0.0,
            accumulator.ranked_search - accumulator.candidate_generation,
        )
        policy = accumulator.policy_arbitration
        other = max(0.0, total - accumulator.ranked_search - policy)
        records.append(
            PPOTacticalEpisodeDecisionCost(
                public_input_sha256=_public_input_sha256(state),
                action=decision.action.name,
                selected_hand_indices=tuple(
                    state.hand.index(card) for card in decision.action.cards
                ),
                search_attempts=tuple(
                    (
                        attempt.horizon,
                        attempt.nodes_evaluated,
                        attempt.max_nodes,
                        attempt.budget_exceeded,
                    )
                    for attempt in decision.search_attempts
                ),
                total_elapsed_seconds=total,
                candidate_generation_elapsed_seconds=accumulator.candidate_generation,
                search_evaluation_elapsed_seconds=search_evaluation,
                policy_arbitration_elapsed_seconds=policy,
                other_elapsed_seconds=other,
            )
        )
        return decision

    engine.decide = decide


def trace_first_ppo_episode_tactical_costs(
    *,
    root_seed: str = "RED-WHITE-PPO-V1",
    clock: Callable[[], float] = perf_counter,
) -> tuple[PPOTacticalEpisodeDecisionCost, ...]:
    """Run episode zero and return ordered per-decision tactical cost evidence."""
    return trace_initial_policy_ppo_episode_tactical_costs(
        episode_index=0,
        root_seed=root_seed,
        clock=clock,
    ).decisions


def trace_initial_policy_ppo_episode_tactical_costs(
    *,
    episode_index: int,
    root_seed: str = "RED-WHITE-PPO-V1",
    clock: Callable[[], float] = perf_counter,
) -> PPOTacticalEpisodeCostReport:
    """Trace one exact pre-optimizer episode without replaying earlier episodes."""
    if not isinstance(root_seed, str) or not root_seed:
        raise ValueError("root_seed must be a nonempty string")
    if not callable(clock):
        raise TypeError("clock must be callable")
    stream_count = PPO_TRAINING_CONTRACT.parallel_environments
    if (
        isinstance(episode_index, bool)
        or not isinstance(episode_index, int)
        or episode_index < 0
    ):
        raise PPOContractError(
            "PPO tactical episode diagnostic requires a nonnegative episode index"
        )

    training_run = PPOTrainingRun.from_seed(root_seed)
    stream_index = episode_index % stream_count
    environment = make_ppo_training_environment(stream_index)
    learner = PPOLearner(training_run)
    records: list[PPOTacticalEpisodeDecisionCost] = []
    _instrument_episode_engine(
        environment._backend._tactical_decision_engine,
        clock,
        records,
    )

    started = float(clock())
    episode = collect_complete_ppo_episode(
        environment,
        training_run,
        episode_index=episode_index,
        policy=learner.model.infer,
    )
    total = float(clock()) - started
    if episode.episode_index != episode_index:
        raise RuntimeError("PPO tactical episode diagnostic episode index drifted")
    tactical = sum(record.total_elapsed_seconds for record in records)
    if any(not math.isfinite(value) or value < 0.0 for value in (total, tactical)):
        raise RuntimeError("PPO tactical episode diagnostic produced invalid timing")
    return PPOTacticalEpisodeCostReport(
        schema=PPO_TACTICAL_EPISODE_COST_SCHEMA,
        root_seed=root_seed,
        episode_index=episode_index,
        stream_index=stream_index,
        game_seed=training_run.game_seed(episode_index),
        environment_transitions=len(episode.decisions),
        total_elapsed_seconds=total,
        tactical_elapsed_seconds=tactical,
        decisions=tuple(records),
    )


def _trace_candidate_subowners(
    *,
    episode_index: int,
    target_index: int,
    expected_prefix: tuple[tuple[object, ...], ...],
    root_seed: str = "RED-WHITE-PPO-V1",
    clock: Callable[[], float] = perf_counter,
) -> PPOTacticalCandidateSubownerReport:
    """Stop after one frozen target and time its planner helpers."""
    if root_seed != "RED-WHITE-PPO-V1":
        raise PPOContractError(
            "candidate sub-owner diagnostic requires root seed RED-WHITE-PPO-V1"
        )
    if not callable(clock):
        raise TypeError("clock must be callable")

    if target_index != len(expected_prefix) - 1:
        raise PPOContractError("candidate sub-owner target must end its exact prefix")
    stream_index = episode_index % PPO_TRAINING_CONTRACT.parallel_environments
    training_run = PPOTrainingRun.from_seed(root_seed)
    environment = make_ppo_training_environment(stream_index)
    learner = PPOLearner(training_run)
    engine = environment._backend._tactical_decision_engine
    helper_accumulator = _ExclusiveHelperAccumulator(clock)
    candidate_elapsed = {"seconds": 0.0}
    evaluation_cache = {"hits": 0, "misses": 0}
    generated_capabilities = {
        "calls": 0,
        "inert": 0,
        "eight_ball": 0,
        "main_generator": 0,
        "sixth_sense": 0,
    }
    state_card_samples = {
        "validation_calls": 0,
        "validation_seconds": 0.0,
        "shallow_copy_calls": 0,
        "shallow_copy_seconds": 0.0,
    }
    reconstruct_type_sampler = _ReconstructTypeSampler(
        clock=clock,
        limit=_RECONSTRUCT_TYPE_SAMPLE_LIMIT,
    )
    instrumented_planners: list[object] = []
    instrumented_evaluators: list[object] = []
    instrumented_score_outcomes: list[object] = []
    instrumented_score_outcome_scorers: list[object] = []
    instrumented_joker_projectors: list[object] = []
    instrumented_action_generators: list[object] = []

    def instrument_evaluator(evaluator) -> None:
        if any(existing is evaluator for existing in instrumented_evaluators):
            return
        instrumented_evaluators.append(evaluator)
        for source_name, report_name in (
            ("_context", "_evaluator_context"),
            ("_discard_value", "_evaluator_discard_value"),
            ("_estimate_play", "_evaluator_estimate_play"),
            ("_has_guaranteed_clearing_play", "_evaluator_guaranteed_clear"),
            ("_retained_structure_value", "_evaluator_retained_structure"),
            ("_hand_for_cards", "_evaluator_hand_for_cards"),
        ):
            function = getattr(evaluator, source_name, None)
            if callable(function):
                setattr(
                    evaluator,
                    source_name,
                    helper_accumulator.wrap(report_name, function),
                )

        score_outcomes = getattr(evaluator, "score_outcomes", None)
        if (
            score_outcomes is not None
            and not any(existing is score_outcomes for existing in instrumented_score_outcomes)
        ):
            instrumented_score_outcomes.append(score_outcomes)
            project = getattr(score_outcomes, "project", None)
            if callable(project):
                score_outcomes.project = helper_accumulator.wrap(
                    "_score_outcomes_project",
                    project,
                )
            project_transition = getattr(score_outcomes, "project_transition", None)
            if callable(project_transition):
                score_outcomes.project_transition = helper_accumulator.wrap(
                    "_score_outcomes_project_transition",
                    project_transition,
                )
            for source_name, report_name in (
                ("_project_hook_transition", "_score_outcomes_hook_transition"),
                (
                    "_project_non_hook_transition",
                    "_score_outcomes_non_hook_transition",
                ),
            ):
                function = getattr(score_outcomes, source_name, None)
                if callable(function):
                    setattr(
                        score_outcomes,
                        source_name,
                        helper_accumulator.wrap(report_name, function),
                    )
            joker_projector = getattr(score_outcomes, "joker_projector", None)
            if (
                joker_projector is not None
                and not any(
                    existing is joker_projector
                    for existing in instrumented_joker_projectors
                )
            ):
                instrumented_joker_projectors.append(joker_projector)
                score = getattr(joker_projector, "score", None)
                if callable(score):
                    joker_projector.score = helper_accumulator.wrap(
                        "_generated_joker_projector_score",
                        score,
                    )
            scorer = getattr(score_outcomes, "scorer", None)
            if (
                scorer is not None
                and not any(
                    existing is scorer
                    for existing in instrumented_score_outcome_scorers
                )
            ):
                instrumented_score_outcome_scorers.append(scorer)
                score = getattr(scorer, "score", None)
                if callable(score):
                    scorer.score = helper_accumulator.wrap(
                        "_score_outcomes_scorer_score",
                        score,
                    )

        action_generator = getattr(evaluator, "action_generator", None)
        if (
            action_generator is not None
            and not any(
                existing is action_generator
                for existing in instrumented_action_generators
            )
        ):
            instrumented_action_generators.append(action_generator)
            generate = getattr(action_generator, "generate_play_actions", None)
            if callable(generate):
                action_generator.generate_play_actions = helper_accumulator.wrap(
                    "_generate_play_actions",
                    generate,
                )

        original_evaluate = evaluator.evaluate

        def counted_evaluate(state, action, *args, **kwargs):
            if helper_accumulator.enabled:
                action_key = getattr(evaluator, "_action_key", None)
                cache = getattr(evaluator, "_outer_d1_evaluation_cache", None)
                if not callable(action_key) or not isinstance(cache, dict):
                    raise RuntimeError("candidate evaluator cache contract drifted")
                hit = (
                    getattr(evaluator, "_outer_d1_cache_state", None) is state
                    and cache.get(action_key(action)) is not None
                )
                evaluation_cache["hits" if hit else "misses"] += 1
            return original_evaluate(state, action, *args, **kwargs)

        evaluator.evaluate = helper_accumulator.wrap(
            "_evaluator_evaluate",
            counted_evaluate,
        )

    def instrument_planner(planner) -> None:
        if any(existing is planner for existing in instrumented_planners):
            return
        instrumented_planners.append(planner)
        evaluator = getattr(planner, "evaluator", None)
        if evaluator is not None:
            instrument_evaluator(evaluator)
        for name in _CANDIDATE_HELPER_NAMES:
            function = getattr(planner, name, None)
            if callable(function):
                setattr(planner, name, helper_accumulator.wrap(name, function))
        original_candidates = planner._candidate_actions

        def timed_candidates(*args, **kwargs):
            if not helper_accumulator.enabled:
                return original_candidates(*args, **kwargs)
            started = float(clock())
            try:
                return original_candidates(*args, **kwargs)
            finally:
                candidate_elapsed["seconds"] += max(
                    0.0,
                    float(clock()) - started,
                )

        planner._candidate_actions = timed_candidates

    instrument_planner(engine.planner)
    original_adaptive_planner = engine._adaptive_planner

    def adaptive_planner(config):
        planner = original_adaptive_planner(config)
        instrument_planner(planner)
        return planner

    engine._adaptive_planner = adaptive_planner
    original_decide = engine.decide
    verified = {"count": 0}

    def decide(state):
        decision_index = verified["count"]
        if decision_index >= len(expected_prefix):
            raise PPOContractError("candidate tactical prefix exceeded target")
        expected = expected_prefix[decision_index]
        digest = _public_input_sha256(state)
        if digest != expected[0]:
            raise PPOContractError(
                f"candidate tactical digest drifted at decision {decision_index}"
            )

        is_target = decision_index == target_index
        helper_accumulator.enabled = is_target
        started = float(clock())
        try:
            decision = original_decide(state)
        finally:
            total = max(0.0, float(clock()) - started)
            helper_accumulator.enabled = False

        action = decision.action.name
        indices = tuple(state.hand.index(card) for card in decision.action.cards)
        attempts = tuple(
            (
                attempt.horizon,
                attempt.nodes_evaluated,
                attempt.max_nodes,
                attempt.budget_exceeded,
            )
            for attempt in decision.search_attempts
        )
        if (action, indices, attempts) != expected[1:]:
            raise PPOContractError(
                f"candidate tactical decision drifted at decision {decision_index}"
            )
        verified["count"] += 1
        if not is_target:
            return decision

        helper_costs = tuple(
            PPOTacticalCandidateHelperCost(
                name=name,
                calls=helper_accumulator.calls.get(name, 0),
                exclusive_elapsed_seconds=helper_accumulator.elapsed.get(name, 0.0),
            )
            for name in _CANDIDATE_HELPER_NAMES
            if helper_accumulator.calls.get(name, 0)
        )
        reconstruct_type_samples = tuple(
            PPOTacticalCandidateReconstructTypeSample(
                type_name=f"{value_type.__module__}.{value_type.__qualname__}",
                sampled_calls=calls,
                exclusive_elapsed_seconds=(
                    reconstruct_type_sampler.elapsed_by_type[value_type]
                ),
            )
            for value_type, calls in sorted(
                reconstruct_type_sampler.calls_by_type.items(),
                key=lambda item: (
                    item[0].__module__,
                    item[0].__qualname__,
                ),
            )
        )
        candidate = candidate_elapsed["seconds"]
        evaluation_calls = helper_accumulator.calls.get("_evaluator_evaluate", 0)
        if evaluation_cache["hits"] + evaluation_cache["misses"] != evaluation_calls:
            raise RuntimeError("candidate evaluator cache accounting drifted")
        residual = max(
            0.0,
            candidate - sum(item.exclusive_elapsed_seconds for item in helper_costs),
        )
        timings = (
            total,
            candidate,
            residual,
            *(item.exclusive_elapsed_seconds for item in helper_costs),
            *(
                item.exclusive_elapsed_seconds
                for item in reconstruct_type_samples
            ),
            state_card_samples["validation_seconds"],
            state_card_samples["shallow_copy_seconds"],
        )
        if any(not math.isfinite(value) or value < 0.0 for value in timings):
            raise RuntimeError(
                "candidate sub-owner diagnostic produced invalid timing"
            )
        report = PPOTacticalCandidateSubownerReport(
            schema=PPO_TACTICAL_CANDIDATE_SUBOWNER_SCHEMA,
            root_seed=root_seed,
            episode_index=episode_index,
            stream_index=stream_index,
            game_seed=training_run.game_seed(episode_index),
            verified_prefix_decisions=verified["count"],
            target_decision_index=target_index,
            public_input_sha256=digest,
            action=action,
            selected_hand_indices=indices,
            search_attempts=attempts,
            evaluation_cache_hits=evaluation_cache["hits"],
            evaluation_cache_misses=evaluation_cache["misses"],
            generated_consumable_transition_calls=generated_capabilities["calls"],
            generated_consumable_inert_calls=generated_capabilities["inert"],
            generated_consumable_eight_ball_capable_calls=generated_capabilities[
                "eight_ball"
            ],
            generated_consumable_main_generator_capable_calls=generated_capabilities[
                "main_generator"
            ],
            generated_consumable_sixth_sense_capable_calls=generated_capabilities[
                "sixth_sense"
            ],
            total_elapsed_seconds=total,
            candidate_generation_elapsed_seconds=candidate,
            helper_costs=helper_costs,
            reconstruct_type_sample_limit=_RECONSTRUCT_TYPE_SAMPLE_LIMIT,
            reconstruct_type_sampled_calls=reconstruct_type_sampler.sampled_calls,
            reconstruct_type_samples=reconstruct_type_samples,
            state_card_sample_limit=_STATE_CARD_SAMPLE_LIMIT,
            state_card_validation_sampled_calls=state_card_samples[
                "validation_calls"
            ],
            state_card_validation_elapsed_seconds=state_card_samples[
                "validation_seconds"
            ],
            state_card_shallow_copy_sampled_calls=state_card_samples[
                "shallow_copy_calls"
            ],
            state_card_shallow_copy_elapsed_seconds=state_card_samples[
                "shallow_copy_seconds"
            ],
            residual_candidate_elapsed_seconds=residual,
        )
        raise _TargetDecisionReached(report)

    engine.decide = decide
    class_instrumentation = (
        (
            LiveGeneratedConsumableScoreOutcomeModel,
            "project_transition",
            "_generated_consumable_project_transition",
        ),
        (
            LiveVisibleCardScoreOutcomeModel,
            "project_transition",
            "_visible_card_project_transition",
        ),
        (
            BalatroState,
            "copy_for_tactical_projection",
            "_state_copy_for_tactical_projection",
        ),
    )
    original_state_deepcopy = balatro_state.deepcopy
    original_state_card_validation = balatro_state._has_exact_scalar_card_state
    original_state_card_shallow_copy = balatro_state._copy_exact_scalar_card
    timed_state_deepcopy = helper_accumulator.wrap(
        "_state_projection_deepcopy",
        original_state_deepcopy,
    )
    state_deepcopy_depth = {"value": 0}

    def nested_state_deepcopy(*args, **kwargs):
        if helper_accumulator.enabled and any(
            frame[0] == "_state_copy_for_tactical_projection"
            for frame in helper_accumulator.stack
        ):
            state_deepcopy_depth["value"] += 1
            try:
                return timed_state_deepcopy(*args, **kwargs)
            finally:
                state_deepcopy_depth["value"] -= 1
        return original_state_deepcopy(*args, **kwargs)

    def nested_copy_internal(report_name, function):
        timed = helper_accumulator.wrap(report_name, function)

        def nested(*args, **kwargs):
            if state_deepcopy_depth["value"]:
                return timed(*args, **kwargs)
            return function(*args, **kwargs)

        return nested

    original_reconstruct = copy_module._reconstruct
    original_copy_dispatch = {
        dict: copy_module._deepcopy_dispatch[dict],
        list: copy_module._deepcopy_dispatch[list],
    }
    installed_class_instrumentation = []
    installed_copy_dispatch = []
    try:
        for owner, name, report_name in class_instrumentation:
            original = getattr(owner, name)
            instrumented = original
            if owner is LiveGeneratedConsumableScoreOutcomeModel:
                def counted_generated_transition(
                    model,
                    hand,
                    state,
                    cards,
                    *args,
                    _original=original,
                    **kwargs,
                ):
                    if helper_accumulator.enabled:
                        eight_ball, main_generator, sixth_sense = (
                            _generated_consumable_capabilities(model, state)
                        )
                        generated_capabilities["calls"] += 1
                        generated_capabilities["eight_ball"] += int(eight_ball)
                        generated_capabilities["main_generator"] += int(
                            main_generator
                        )
                        generated_capabilities["sixth_sense"] += int(sixth_sense)
                        generated_capabilities["inert"] += int(
                            not (eight_ball or main_generator or sixth_sense)
                        )
                    return _original(model, hand, state, cards, *args, **kwargs)

                instrumented = counted_generated_transition
            setattr(
                owner,
                name,
                helper_accumulator.wrap(report_name, instrumented),
            )
            installed_class_instrumentation.append((owner, name, original))
        balatro_state.deepcopy = nested_state_deepcopy
        installed_class_instrumentation.append(
            (balatro_state, "deepcopy", original_state_deepcopy)
        )

        def sampled_state_card_call(kind, function, *args, **kwargs):
            calls_key = f"{kind}_calls"
            seconds_key = f"{kind}_seconds"
            if (
                not helper_accumulator.enabled
                or state_card_samples[calls_key] >= _STATE_CARD_SAMPLE_LIMIT
            ):
                return function(*args, **kwargs)
            started = float(clock())
            try:
                return function(*args, **kwargs)
            finally:
                state_card_samples[calls_key] += 1
                state_card_samples[seconds_key] += max(
                    0.0,
                    float(clock()) - started,
                )
                if all(
                    state_card_samples[f"{sample_kind}_calls"]
                    >= _STATE_CARD_SAMPLE_LIMIT
                    for sample_kind in ("validation", "shallow_copy")
                ):
                    balatro_state._has_exact_scalar_card_state = (
                        original_state_card_validation
                    )
                    balatro_state._copy_exact_scalar_card = (
                        original_state_card_shallow_copy
                    )

        def sampled_state_card_validation(*args, **kwargs):
            return sampled_state_card_call(
                "validation",
                original_state_card_validation,
                *args,
                **kwargs,
            )

        def sampled_state_card_shallow_copy(*args, **kwargs):
            return sampled_state_card_call(
                "shallow_copy",
                original_state_card_shallow_copy,
                *args,
                **kwargs,
            )

        balatro_state._has_exact_scalar_card_state = sampled_state_card_validation
        installed_class_instrumentation.append(
            (
                balatro_state,
                "_has_exact_scalar_card_state",
                original_state_card_validation,
            )
        )
        balatro_state._copy_exact_scalar_card = sampled_state_card_shallow_copy
        installed_class_instrumentation.append(
            (
                balatro_state,
                "_copy_exact_scalar_card",
                original_state_card_shallow_copy,
            )
        )
        timed_reconstruct = nested_copy_internal(
            "_state_deepcopy_reconstruct",
            original_reconstruct,
        )

        sampled_reconstruct = reconstruct_type_sampler.wrap_reconstruct(
            timed_reconstruct,
        )

        def counted_reconstruct(value, *args, **kwargs):
            if state_deepcopy_depth["value"]:
                return sampled_reconstruct(value, *args, **kwargs)
            return timed_reconstruct(value, *args, **kwargs)

        copy_module._reconstruct = counted_reconstruct
        installed_class_instrumentation.append(
            (copy_module, "_reconstruct", original_reconstruct)
        )
        for value_type, report_name in (
            (dict, "_state_deepcopy_dict"),
            (list, "_state_deepcopy_list"),
        ):
            original = original_copy_dispatch[value_type]
            timed_internal = nested_copy_internal(report_name, original)
            sampled_child = reconstruct_type_sampler.wrap_child(timed_internal)

            def sampled_internal(
                *args,
                _timed=timed_internal,
                _sampled=sampled_child,
                **kwargs,
            ):
                if state_deepcopy_depth["value"]:
                    return _sampled(*args, **kwargs)
                return _timed(*args, **kwargs)

            copy_module._deepcopy_dispatch[value_type] = sampled_internal
            installed_copy_dispatch.append((value_type, original))
        try:
            collect_complete_ppo_episode(
                environment,
                training_run,
                episode_index=episode_index,
                policy=learner.model.infer,
            )
        except _TargetDecisionReached as reached:
            return reached.report
    finally:
        for value_type, original in reversed(installed_copy_dispatch):
            copy_module._deepcopy_dispatch[value_type] = original
        for owner, name, original in reversed(installed_class_instrumentation):
            setattr(owner, name, original)
    raise PPOContractError("candidate sub-owner target was not reached")


def trace_episode_seven_candidate_subowners(
    *,
    root_seed: str = "RED-WHITE-PPO-V1",
    clock: Callable[[], float] = perf_counter,
) -> PPOTacticalCandidateSubownerReport:
    """Stop after the frozen episode-seven target and time its planner helpers."""
    return _trace_candidate_subowners(
        episode_index=7,
        target_index=len(_EPISODE_7_EXPECTED_PREFIX) - 1,
        expected_prefix=_EPISODE_7_EXPECTED_PREFIX,
        root_seed=root_seed,
        clock=clock,
    )


def trace_episode_43_decision_11_candidate_subowners(
    *,
    root_seed: str = "RED-WHITE-PPO-V1",
    clock: Callable[[], float] = perf_counter,
) -> PPOTacticalCandidateSubownerReport:
    """Stop at verified episode-43 decision 11 and time candidate subowners."""
    return _trace_candidate_subowners(
        episode_index=43,
        target_index=len(_EPISODE_43_DECISION_11_EXPECTED_PREFIX) - 1,
        expected_prefix=_EPISODE_43_DECISION_11_EXPECTED_PREFIX,
        root_seed=root_seed,
        clock=clock,
    )


def measure_ppo_tactical_cost(
    *,
    root_seed: str = "RED-WHITE-PPO-V1",
    clock: Callable[[], float] = perf_counter,
) -> PPOTacticalCostReport:
    """Measure one exact production decision without changing its search contract."""
    if not isinstance(root_seed, str) or not root_seed:
        raise ValueError("root_seed must be a nonempty string")
    if not callable(clock):
        raise TypeError("clock must be callable")

    training_run = PPOTrainingRun.from_seed(root_seed)
    game_seed = training_run.game_seed(0)
    run = pristine_red_white_reset(game_seed)
    run = activate_selected_blind_progression(run)
    run = select_blind_exact(run)
    state = public_observation_state(run.public)

    environment = make_ppo_training_environment(0)
    engine = environment._backend._tactical_decision_engine
    accumulator = _CostAccumulator()
    _instrument_planner(engine.planner, clock, accumulator)

    original_adaptive_planner = engine._adaptive_planner

    def instrumented_adaptive_planner(config):
        planner = original_adaptive_planner(config)
        _instrument_planner(planner, clock, accumulator)
        return planner

    engine._adaptive_planner = instrumented_adaptive_planner
    engine.rank_plans = _timed_call(
        clock,
        accumulator,
        "ranked_search",
        engine.rank_plans,
    )
    engine.policy.decide = _timed_call(
        clock,
        accumulator,
        "policy_arbitration",
        engine.policy.decide,
    )

    started = float(clock())
    decision = engine.decide(state)
    total = float(clock()) - started
    search_evaluation = max(
        0.0,
        accumulator.ranked_search - accumulator.candidate_generation,
    )
    other = max(
        0.0,
        total - accumulator.ranked_search - accumulator.policy_arbitration,
    )
    timings = (
        total,
        accumulator.candidate_generation,
        search_evaluation,
        accumulator.policy_arbitration,
        other,
    )
    if any(not math.isfinite(value) or value < 0.0 for value in timings):
        raise RuntimeError("PPO tactical diagnostic produced invalid timing")

    return PPOTacticalCostReport(
        schema=PPO_TACTICAL_COST_SCHEMA,
        workload=PPO_TACTICAL_COST_WORKLOAD,
        root_seed=root_seed,
        game_seed=game_seed,
        action=decision.action.name,
        selected_hand_indices=tuple(
            state.hand.index(card) for card in decision.action.cards
        ),
        search_attempts=tuple(
            (
                attempt.horizon,
                attempt.nodes_evaluated,
                attempt.max_nodes,
                attempt.budget_exceeded,
            )
            for attempt in decision.search_attempts
        ),
        total_elapsed_seconds=total,
        candidate_generation_elapsed_seconds=accumulator.candidate_generation,
        search_evaluation_elapsed_seconds=search_evaluation,
        policy_arbitration_elapsed_seconds=accumulator.policy_arbitration,
        other_elapsed_seconds=other,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-seed", default="RED-WHITE-PPO-V1")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--episode-index", type=int)
    target.add_argument("--episode-seven-candidate-subowners", action="store_true")
    target.add_argument(
        "--episode-43-decision-11-candidate-subowners",
        action="store_true",
    )
    target.add_argument("--episode-seven-schedule-probe", action="store_true")
    target.add_argument("--episode-seven-horizon-two-parity", action="store_true")
    target.add_argument("--episode-zero-horizon-two-parity", action="store_true")
    target.add_argument("--episode-seven-selective-escalation", action="store_true")
    parser.add_argument("--output-path")
    arguments = parser.parse_args(argv)
    output_capable = (
        arguments.episode_index is not None
        or arguments.episode_seven_candidate_subowners
        or arguments.episode_43_decision_11_candidate_subowners
    )
    if arguments.output_path is not None and not output_capable:
        parser.error(
            "--output-path requires an episode or candidate-subowner trace"
        )
    report = (
        trace_episode_43_decision_11_candidate_subowners(
            root_seed=arguments.root_seed
        )
        if arguments.episode_43_decision_11_candidate_subowners
        else probe_episode_seven_selective_escalation(root_seed=arguments.root_seed)
        if arguments.episode_seven_selective_escalation
        else probe_episode_zero_horizon_two_parity(root_seed=arguments.root_seed)
        if arguments.episode_zero_horizon_two_parity
        else probe_episode_seven_horizon_two_parity(root_seed=arguments.root_seed)
        if arguments.episode_seven_horizon_two_parity
        else probe_episode_seven_bounded_schedules(root_seed=arguments.root_seed)
        if arguments.episode_seven_schedule_probe
        else trace_episode_seven_candidate_subowners(root_seed=arguments.root_seed)
        if arguments.episode_seven_candidate_subowners
        else measure_ppo_tactical_cost(root_seed=arguments.root_seed)
        if arguments.episode_index is None
        else trace_initial_policy_ppo_episode_tactical_costs(
            episode_index=arguments.episode_index,
            root_seed=arguments.root_seed,
        )
    )
    if arguments.output_path is None:
        print(report.to_json())
    else:
        if isinstance(report, PPOTacticalEpisodeCostReport):
            report_sha256 = write_ppo_tactical_episode_report(
                arguments.output_path,
                report,
            )
            summary = {
                "schema": report.schema,
                "output_path": str(Path(arguments.output_path)),
                "report_sha256": report_sha256,
                "episode_index": report.episode_index,
                "decision_count": len(report.decisions),
                "total_elapsed_seconds": report.total_elapsed_seconds,
            }
        elif isinstance(report, PPOTacticalCandidateSubownerReport):
            report_sha256 = write_ppo_tactical_candidate_subowner_report(
                arguments.output_path,
                report,
            )
            summary = {
                "schema": report.schema,
                "output_path": str(Path(arguments.output_path)),
                "report_sha256": report_sha256,
                "episode_index": report.episode_index,
                "target_decision_index": report.target_decision_index,
                "total_elapsed_seconds": report.total_elapsed_seconds,
            }
        else:
            parser.error("selected tactical diagnostic cannot persist a report")
        print(
            json.dumps(
                summary,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
