from types import SimpleNamespace

from games.balatro.build.joker_semantics import CONSUMABLE_DUPLICATE
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


class _EqualPlanetUpgradeEvaluator:
    """Make Pair/Flush Planet score gains equal so B3 breaks the tie."""

    def __init__(self):
        self.action_generator = _ActionGenerator()

    def project_play(self, state, action):
        del action
        investment = sum(
            max(0, int(state.hand_levels.get(hand, 1)) - 1)
            for hand in ("PAIR", "FLUSH")
        )
        score = 100.0 + 15.0 * investment
        return SimpleNamespace(
            clear_probability=0.0,
            expected_hand_score=score,
            hand_score=int(score),
            maximum_hand_score=int(score),
            joker_projection_complete=True,
        )


class _EqualAllPlanetUpgradeEvaluator:
    """Make every one-level Planet upgrade equally valuable immediately."""

    def __init__(self):
        self.action_generator = _ActionGenerator()

    def project_play(self, state, action):
        del action
        investment = sum(
            max(0, int(level) - 1)
            for level in state.hand_levels.values()
        )
        score = 100.0 + 15.0 * investment
        return SimpleNamespace(
            clear_probability=0.0,
            expected_hand_score=score,
            hand_score=int(score),
            maximum_hand_score=int(score),
            joker_projection_complete=True,
        )


class _EqualPlanetOutlook:
    def evaluate(self, state, planet):
        del state, planet
        return SimpleNamespace(
            observed_plays=1,
            total_observed_plays=2,
            observed_frequency=0.5,
            structural_feasibility=0.5,
            expected_future_frequency=0.5,
            marginal_level_gain=1.0,
            future_value=0.5,
            speculative=False,
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


def _standard_deck():
    ranks = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
    suits = ("Hearts", "Diamonds", "Clubs", "Spades")
    return [BalatroCard(rank, suit) for suit in suits for rank in ranks]


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


def test_d7_future_outlook_breaks_equal_immediate_value_against_neptune():
    state = _state()
    state.jokers = []
    state.hand_play_counts.clear()
    state.owned_deck = _standard_deck()
    state.hand_size = 8
    mercury = create_planet("MERCURY")
    neptune = create_planet("NEPTUNE")
    state.consumables = [neptune, mercury]
    policy = LivePlanetPolicy(hand_evaluator=_EqualAllPlanetUpgradeEvaluator())

    decisions = policy.recommend_inventory(state)

    assert decisions[0].planet is mercury
    assert decisions[0].immediate_score_gain == decisions[1].immediate_score_gain
    assert decisions[0].future_value > decisions[1].future_value
    assert decisions[1].structural_feasibility < 0.01
    assert any("Planet speculative=True" in note for note in decisions[1].rationale)


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
