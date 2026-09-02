from types import SimpleNamespace

import pytest

import games.balatro.live.planet_policy as planet_policy_module
from games.balatro.build.joker_semantics import CONSUMABLE_DUPLICATE
from games.balatro.live.planet_policy import HOLD, LivePlanetPolicy
from games.balatro.planet_strategy_delta import project_planet_use
from games.balatro.planets import create_planet
from games.balatro.shop_consumable_policy import (
    BUY,
    ConsumableAcquisitionPolicy,
    ConsumableAcquisitionThresholds,
)
from games.balatro.state import BalatroState


class _PositiveEvaluator:
    def evaluate(self, candidate, state):
        del candidate, state
        return SimpleNamespace(total_gain=2.0, rationale=("fixture positive build value",))


class _ActionGenerator:
    def generate_play_actions(self, state):
        del state
        return [object()]


class _DeterministicHandEvaluator:
    def __init__(self):
        self.action_generator = _ActionGenerator()

    def project_play(self, state, action):
        del action
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
        del joker
        return _DuplicateDescriptor()


class _Blind:
    requirement = 100_000

    def copy(self):
        return _Blind()


def _no_economy_thresholds() -> ConsumableAcquisitionThresholds:
    return ConsumableAcquisitionThresholds(
        minimum_purchase_advantage=0.0,
        minimum_buy_and_use_advantage=0.0,
        price_weight=0.0,
        interest_weight=0.0,
        reserve_weight=0.0,
        last_consumable_slot_penalty=0.0,
    )


def _decision_debug(decision) -> str:
    decide = ConsumableAcquisitionPolicy.decide
    code = getattr(decide, "__code__", None)
    return (
        f"decision={decision!r}; "
        f"decide_module={getattr(decide, '__module__', None)!r}; "
        f"decide_qualname={getattr(decide, '__qualname__', None)!r}; "
        f"decide_file={getattr(code, 'co_filename', None)!r}; "
        f"planet_relevance_installed="
        f"{getattr(ConsumableAcquisitionPolicy, '_planet_relevance_installed', False)!r}"
    )


def _held_pair_planet_state() -> tuple[BalatroState, object]:
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand_levels["PAIR"] = 1
    state.hand_play_counts["PAIR"] = 5
    state.hand = []
    state.deck = []
    state.hands_remaining = 4
    state.score = 0
    state.blind = _Blind()
    state.consumable_slots = 2
    mercury = create_planet("MERCURY")
    state.consumables = [mercury]
    return state, mercury


def test_h4_exact_held_planet_projection_uses_real_planet_semantics_without_mutation():
    state, mercury = _held_pair_planet_state()

    projected = project_planet_use(state, mercury, held=True)

    assert projected is not None
    assert projected is not state
    assert state.hand_levels["PAIR"] == 1
    assert state.consumables == [mercury]
    assert projected.hand_levels["PAIR"] == 2
    assert projected.consumables == []


def test_h4_shop_planet_score_adds_point_one_times_canonical_strategy_delta(monkeypatch):
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 20
    state.consumable_slots = 2
    mercury = create_planet("MERCURY")
    mercury.price = 0

    monkeypatch.setattr(
        "games.balatro.shop_consumable_policy.planet_strategy_delta",
        lambda current, planet, held: SimpleNamespace(value=6.0),
    )

    decision = ConsumableAcquisitionPolicy(
        _no_economy_thresholds(),
        evaluator=_PositiveEvaluator(),
    ).decide(state, mercury)

    assert decision.action == BUY, _decision_debug(decision)
    assert decision.selected is not None
    assert decision.selected.strategy_delta_value == pytest.approx(6.0)
    assert decision.selected.strategy_adjustment == pytest.approx(0.6)
    assert decision.selected.total_advantage == pytest.approx(2.6)


def test_h4_held_planet_strategy_delta_cannot_override_tactical_hold(monkeypatch):
    state, mercury = _held_pair_planet_state()
    state.jokers = [SimpleNamespace(name="duplicate fixture")]
    policy = LivePlanetPolicy(
        hand_evaluator=_DeterministicHandEvaluator(),
        joker_analyzer=_DuplicateAnalyzer(),
    )

    monkeypatch.setattr(
        planet_policy_module,
        "planet_strategy_delta",
        lambda current, planet, held: SimpleNamespace(value=10_000.0),
    )
    positive = policy.recommend(state, mercury)

    monkeypatch.setattr(
        planet_policy_module,
        "planet_strategy_delta",
        lambda current, planet, held: SimpleNamespace(value=-10_000.0),
    )
    negative = policy.recommend(state, mercury)

    assert positive.decision == HOLD
    assert negative.decision == HOLD
    assert positive.strategy_delta_value == pytest.approx(10_000.0)
    assert negative.strategy_delta_value == pytest.approx(-10_000.0)
    assert positive.duplicate_hold_value == pytest.approx(1.0)
    assert negative.duplicate_hold_value == pytest.approx(1.0)


def test_h4_production_shop_has_no_legacy_bond_rank_planet_veto():
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 20
    state.consumable_slots = 2
    state.hand_levels["STRAIGHT_FLUSH"] = 1
    state.hand_play_counts["STRAIGHT_FLUSH"] = 0
    neptune = create_planet("NEPTUNE")
    neptune.price = 0

    decision = ConsumableAcquisitionPolicy(
        _no_economy_thresholds(),
        evaluator=_PositiveEvaluator(),
    ).decide(state, neptune)

    assert decision.action == BUY, _decision_debug(decision)
    assert decision.selected is not None
    assert all("Planet relevance veto" not in note for note in decision.rationale)
