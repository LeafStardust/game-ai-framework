from types import SimpleNamespace

from games.balatro.build.high_priestess_expectation import HighPriestessExpectationEvaluator
from games.balatro.planets import create_planet
from games.balatro.shop_consumable_policy import ConsumableAcquisitionPolicy
from games.balatro.state import BalatroState
from games.balatro.voucher_parent_literal_policy import VoucherParentLiteralEvaluator


class _ConstantPlanetEstimator:
    def estimate(self, state, action):
        return 1.0, ("test value",)


class ConstellationJoker:
    debuffed = False


class _BlankParentShopPolicy:
    price_weight = 0.35


def _state() -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    return state


def test_high_priestess_excludes_held_planet_without_showman():
    state = _state()
    state.consumable_slots = 3
    state.consumables = [create_planet("PLUTO")]

    result = HighPriestessExpectationEvaluator(
        item_estimator=_ConstantPlanetEstimator()
    ).evaluate(state)

    assert result.available
    assert result.complete
    assert result.generated_count == 2
    assert "Pluto" not in {outcome.planet_name for outcome in result.outcomes}
    assert any("held duplicate exclusions=Pluto" in note for note in result.rationale)


def test_high_priestess_showman_allows_held_planet_duplicate():
    state = _state()
    state.consumable_slots = 3
    state.consumables = [create_planet("PLUTO")]
    state.jokers = [SimpleNamespace(name="Showman")]

    result = HighPriestessExpectationEvaluator(
        item_estimator=_ConstantPlanetEstimator()
    ).evaluate(state)

    assert result.available
    assert result.complete
    assert result.generated_count == 2
    assert "Pluto" in {outcome.planet_name for outcome in result.outcomes}
    assert any("duplicates allowed" in note for note in result.rationale)


def test_planet_scaler_buy_and_use_has_zero_synthetic_immediate_gain():
    state = _state()
    state.money = 20
    state.jokers = [ConstellationJoker()]
    state.hand_levels["HIGH_CARD"] = 1
    candidate = create_planet("PLUTO")

    policy = ConsumableAcquisitionPolicy()
    immediate = policy._immediate_use_case(state, candidate)

    assert immediate is not None
    immediate_gain, rationale = immediate
    assert immediate_gain == 0.0

    option = policy._score_buy_and_use(
        state,
        candidate,
        build_gain=0.0,
        immediate_gain=immediate_gain,
        rationale=rationale,
    )
    assert option.eligible
    assert option.immediate_gain == 0.0
    assert any("no synthetic immediate utility" in note for note in option.rationale)


def test_blank_parent_progression_ends_when_antimatter_unlocks():
    evaluator = VoucherParentLiteralEvaluator.__new__(VoucherParentLiteralEvaluator)
    evaluator.shop_policy = _BlankParentShopPolicy()

    state = _state()
    state.antimatter_unlock_observed = True
    state.antimatter_unlocked = True

    complete, value, rationale = evaluator._blank(state, price=10)

    assert complete
    assert value == 0.0
    assert any("already unlocked" in note for note in rationale)


def test_blank_parent_progression_only_covers_direct_price_while_locked():
    evaluator = VoucherParentLiteralEvaluator.__new__(VoucherParentLiteralEvaluator)
    evaluator.shop_policy = _BlankParentShopPolicy()

    state = _state()
    state.antimatter_unlock_observed = True
    state.antimatter_unlocked = False

    complete, value, rationale = evaluator._blank(state, price=10)

    assert complete
    assert value > 10 * _BlankParentShopPolicy.price_weight
    assert value < 10 * _BlankParentShopPolicy.price_weight + 1.0
    assert any("lost interest" in note for note in rationale)
    assert any("once Antimatter unlocks" in note for note in rationale)
