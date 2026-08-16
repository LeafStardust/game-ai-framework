from types import SimpleNamespace

from games.balatro.card import BalatroCard
from games.balatro.live.consumable_timing import LiveConsumableTimingPolicy
from games.balatro.live.planet_policy import (
    HOLD,
    USE,
    LivePlanetPolicy,
    PlanetPolicyThresholds,
)
from games.balatro.planets import create_planet
from games.balatro.state import BalatroState
from games.balatro.build.joker_semantics import CONSUMABLE_DUPLICATE


class _Blind:
    def __init__(self, requirement=100_000):
        self.requirement = requirement

    def copy(self):
        return _Blind(self.requirement)


class _ActionGenerator:
    def generate_play_actions(self, state):
        return [object()]


class _DeterministicHandEvaluator:
    def __init__(self):
        self.action_generator = _ActionGenerator()

    def project_play(self, state, action):
        level = int(state.hand_levels.get("PAIR", 1))
        score = 100.0 + 15.0 * (level - 1)
        return SimpleNamespace(
            clear_probability=0.0,
            expected_hand_score=score,
            hand_score=int(score),
            maximum_hand_score=int(score),
            joker_projection_complete=True,
        )


class _DuplicateDescriptor:
    produces = frozenset({CONSUMABLE_DUPLICATE})

    def feature_magnitude(self, feature):
        assert feature == CONSUMABLE_DUPLICATE
        return 1.0


class _DuplicateAnalyzer:
    def describe(self, joker):
        return _DuplicateDescriptor()


def _state(*, hands_remaining=4, phase="SELECTING_HAND"):
    state = BalatroState()
    state.phase = phase
    state.hand = [BalatroCard("8", "Hearts"), BalatroCard("8", "Clubs")]
    state.deck = [BalatroCard("8", "Hearts"), BalatroCard("8", "Clubs")]
    state.hands_remaining = hands_remaining
    state.score = 0
    state.blind = _Blind()
    state.hand_levels["PAIR"] = 1
    state.hand_levels["FLUSH"] = 1
    state.hand_play_counts["PAIR"] = 5
    state.hand_play_counts["FLUSH"] = 1
    state.consumable_slots = 2
    return state


def test_planet_defaults_to_immediate_use_without_positive_hold_signal():
    state = _state()
    mercury = create_planet("MERCURY")
    state.consumables = [mercury]

    decision = LivePlanetPolicy().recommend(state, mercury)

    assert decision.decision == USE
    assert decision.level_gain == 1
    assert decision.duplicate_hold_value == 0.0
    assert any("no modeled positive hold advantage" in note for note in decision.rationale)


def test_consumable_duplication_is_positive_modeled_planet_hold_value():
    state = _state()
    mercury = create_planet("MERCURY")
    state.consumables = [mercury]
    state.jokers = [SimpleNamespace(name="duplicate fixture")]
    policy = LivePlanetPolicy(
        hand_evaluator=_DeterministicHandEvaluator(),
        joker_analyzer=_DuplicateAnalyzer(),
    )

    decision = policy.recommend(state, mercury)

    assert decision.decision == HOLD
    assert decision.duplicate_hold_value == 1.0
    assert any("consumable-duplication" in note for note in decision.rationale)


def test_duplicate_hold_threshold_is_independent_and_configurable():
    state = _state()
    mercury = create_planet("MERCURY")
    state.consumables = [mercury]
    state.jokers = [SimpleNamespace(name="duplicate fixture")]
    policy = LivePlanetPolicy(
        thresholds=PlanetPolicyThresholds(duplicate_hold_minimum=1.01),
        hand_evaluator=_DeterministicHandEvaluator(),
        joker_analyzer=_DuplicateAnalyzer(),
    )

    decision = policy.recommend(state, mercury)

    assert decision.decision == USE
    assert decision.duplicate_hold_value == 1.0


def test_final_hand_urgency_overrides_positive_duplicate_hold_value():
    state = _state(hands_remaining=1)
    mercury = create_planet("MERCURY")
    state.consumables = [mercury]
    state.jokers = [SimpleNamespace(name="duplicate fixture")]
    policy = LivePlanetPolicy(
        hand_evaluator=_DeterministicHandEvaluator(),
        joker_analyzer=_DuplicateAnalyzer(),
    )

    decision = policy.recommend(state, mercury)

    assert decision.decision == USE
    assert decision.immediate_score_gain > 0.0
    assert any("final hand" in note for note in decision.rationale)


def test_full_consumable_slots_override_positive_duplicate_hold_value():
    state = _state()
    mercury = create_planet("MERCURY")
    state.consumables = [mercury]
    state.consumable_slots = 1
    state.jokers = [SimpleNamespace(name="duplicate fixture")]
    policy = LivePlanetPolicy(
        hand_evaluator=_DeterministicHandEvaluator(),
        joker_analyzer=_DuplicateAnalyzer(),
    )

    decision = policy.recommend(state, mercury)

    assert decision.decision == USE
    assert any("full consumable slots" in note for note in decision.rationale)


def test_planet_inventory_selection_prefers_current_build_hand_upgrade():
    state = _state()
    mercury = create_planet("MERCURY")
    jupiter = create_planet("JUPITER")
    state.consumables = [jupiter, mercury]

    decisions = LivePlanetPolicy().recommend_inventory(state)

    assert len(decisions) == 2
    assert decisions[0].planet is mercury
    assert decisions[0].immediate_score_gain > decisions[1].immediate_score_gain


def test_production_consumable_timing_routes_planet_through_d7_policy():
    state = _state()
    mercury = create_planet("MERCURY")
    state.consumables = [mercury]

    recommendation = LiveConsumableTimingPolicy().recommend(state, mercury)

    assert recommendation.decision == USE
    assert recommendation.target is None
    assert recommendation.after_projection is not None
    assert recommendation.to_action() is not None
    assert recommendation.to_action().target is mercury
    assert any("Planet=Mercury" in note for note in recommendation.rationale)


def test_planet_policy_simulation_does_not_mutate_authoritative_state():
    state = _state()
    mercury = create_planet("MERCURY")
    state.consumables = [mercury]
    before_level = state.hand_levels["PAIR"]

    LivePlanetPolicy().recommend(state, mercury)

    assert state.hand_levels["PAIR"] == before_level
    assert state.consumables == [mercury]


def test_shop_planet_remains_fail_closed_until_d7_live_execution_slice():
    state = _state(phase="SHOP")
    mercury = create_planet("MERCURY")
    state.consumables = [mercury]

    recommendation = LiveConsumableTimingPolicy().recommend(state, mercury)

    assert recommendation.decision == HOLD
    assert any("requires SELECTING_HAND" in note for note in recommendation.rationale)
