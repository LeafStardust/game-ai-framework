from games.balatro.build.effects import EffectDescriptor
from games.balatro.build.joker_strategy import JokerBuildValueWeights
from games.balatro.build.synergy import ContextualBuildEvaluation
from games.balatro.joker import Joker, JokerContext
from games.balatro.joker_policy import HOLD, REPLACE, JokerAcquisitionPolicy, JokerAcquisitionThresholds
from games.balatro.state import BalatroState
from games.balatro.strategy import BANNED, BRONZE, StrategyDefinition, BalatroStrategyTracker
from games.balatro.strategy_value import (
    StrategyAdjustedJokerBuildValue,
    StrategyAwareJokerBuildTransitionPlanner,
    StrategyAwareJokerBuildValueEvaluator,
)


class AnchorJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        return context


class ConflictJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        return context


class ReinforcerJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        return context


class NeutralContextualEvaluator:
    def evaluate(self, joker, state):
        return ContextualBuildEvaluation(
            candidate=type(joker).__name__,
            descriptor=EffectDescriptor(
                source=type(joker).__name__,
                kind="JOKER",
            ),
            intrinsic_gain=0.0,
            interaction_gain=0.0,
            total_gain=0.0,
            matched_requirements=(),
            unmet_requirements=(),
            matched_scaling=(),
            amplified_features=(),
            reverse_amplified_features=(),
            pair_interactions=(),
            contributions=(),
        )


class FixedProbeStrategyEvaluator(StrategyAwareJokerBuildValueEvaluator):
    def _direct_scoring_gain(self, state, joker):
        return float(getattr(joker, "fixed_probe_gain", 0.0))


def _tracker():
    definition = StrategyDefinition(
        strategy_id="pair",
        name="Pair",
        primary_hands=("PAIR",),
        gold_jokers=frozenset({"anchorjoker"}),
        bronze_jokers=frozenset({"reinforcerjoker"}),
        banned_jokers=frozenset({"conflictjoker"}),
    )
    return BalatroStrategyTracker({"pair": definition})


def _state(*, conflict_probe_gain: float = 0.0):
    state = BalatroState()
    state.phase = "SHOP"
    state.ante = 6
    state.money = 20
    state.joker_slots = 3
    conflict = ConflictJoker()
    conflict.fixed_probe_gain = float(conflict_probe_gain)
    state.jokers = [AnchorJoker(), AnchorJoker(), conflict]
    return state


def _planner():
    evaluator = FixedProbeStrategyEvaluator(
        strategy_tracker=_tracker(),
        contextual=NeutralContextualEvaluator(),
        # Keep the survival regression above the deliberately stronger Gold-core
        # strategy pressure introduced by the 8/3/1 evidence scale.
        weights=JokerBuildValueWeights(direct_scoring_cap=30.0),
    )
    return StrategyAwareJokerBuildTransitionPlanner(evaluator=evaluator)


def _thresholds():
    return JokerAcquisitionThresholds(
        minimum_purchase_advantage=0.0,
        minimum_replacement_advantage=0.0,
        price_weight=0.0,
        interest_weight=0.0,
        reserve_weight=0.0,
        last_joker_slot_penalty=0.0,
        penultimate_joker_slot_penalty=0.0,
    )


def test_banned_incumbent_becomes_preferred_replacement_target_for_active_strategy():
    state = _state()
    candidate = ReinforcerJoker()
    candidate.cost = 0

    planner = _planner()
    transition = planner.plan(state, candidate)
    decision = JokerAcquisitionPolicy(
        _thresholds(),
        transition_planner=planner,
    ).decide(state, candidate)

    assert transition.action == REPLACE
    assert transition.replacement is not None
    assert transition.replacement.replace_index == 2
    assert isinstance(
        transition.replacement.incumbent_value,
        StrategyAdjustedJokerBuildValue,
    )
    assert transition.replacement.incumbent_value.strategy_tier == BANNED
    assert transition.replacement.incumbent_value.strategic_adjustment < 0.0
    assert transition.replacement.candidate_value.strategy_tier == BRONZE
    assert transition.replacement.candidate_value.strategic_adjustment > 0.0
    assert any(
        "universal-strategy conflict replacement pressure" in note
        for note in transition.replacement.rationale
    )
    assert decision.action == REPLACE
    assert decision.selected is not None
    assert decision.selected.replace_index == 2


def test_strategy_conflict_does_not_force_sale_when_incumbent_carries_build_survival():
    state = _state(conflict_probe_gain=10.0)
    candidate = ReinforcerJoker()
    candidate.cost = 0

    planner = _planner()
    transition = planner.plan(state, candidate)
    conflict_option = next(
        option
        for option in transition.alternatives
        if option.replace_index == 2
    )
    decision = JokerAcquisitionPolicy(
        _thresholds(),
        transition_planner=planner,
    ).decide(state, candidate)

    assert isinstance(conflict_option.incumbent_value, StrategyAdjustedJokerBuildValue)
    assert conflict_option.incumbent_value.strategy_tier == BANNED
    assert conflict_option.incumbent_value.strategic_adjustment < 0.0
    assert conflict_option.incumbent_value.base_total_gain > 0.0
    assert conflict_option.build_delta < 0.0
    assert transition.action == HOLD
    assert any(
        "scoring/context survival value can override strategic purity" in note
        for note in transition.rationale
    )
    assert decision.action == HOLD
