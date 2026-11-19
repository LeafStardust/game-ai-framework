import pytest

from games.balatro.env.joker_sale import (
    can_sell_joker_exact,
    sell_joker_exact,
)
from games.balatro.env.actions import EnvAction
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.drunkard import DrunkardJoker
from games.balatro.jokers.golden_joker import GoldenJoker
from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.juggler import JugglerJoker
from games.balatro.jokers.troubadour import TroubadourJoker
from games.balatro.state import BalatroState


def _shop_run(joker=None) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = 7
    selected = joker or FlatMultJoker()
    selected.sell_cost = 3
    state.jokers = [selected]
    return HeadlessRunState(public=state, seed="SELL-JOKER")


def test_env_r3_exact_shop_joker_sale_credits_and_removes_inventory_only_joker():
    run = _shop_run()
    before_rng = run.rng_snapshot()

    assert can_sell_joker_exact(run, 0)
    result = sell_joker_exact(run, 0)

    assert result.public.money == 10
    assert result.public.jokers == []
    assert result.public.phase == "SHOP"
    assert result.public.shop_active is True
    assert result.rng_snapshot() == before_rng
    assert run.public.money == 7
    assert len(run.public.jokers) == 1
    assert run.rng_snapshot() == before_rng


@pytest.mark.parametrize("phase", ["BLIND_SELECT", "SELECTING_HAND", "BUFFOON_PACK"])
def test_env_r3_exact_sale_fails_closed_outside_active_main_shop(phase):
    run = _shop_run()
    run.public.phase = phase

    assert not can_sell_joker_exact(run, 0)
    with pytest.raises(HeadlessTransitionError, match="active SHOP"):
        sell_joker_exact(run, 0)

    run = _shop_run()
    run.public.shop_active = False
    assert not can_sell_joker_exact(run, 0)


def test_env_r3_exact_sale_fails_closed_for_unowned_inverse_and_metadata():
    run = _shop_run(TroubadourJoker())
    assert not can_sell_joker_exact(run, 0)
    with pytest.raises(HeadlessTransitionError, match="inverse lifecycle"):
        sell_joker_exact(run, 0)

    for field, value, message in (
        ("eternal", True, "Eternal"),
        ("edition", "NEGATIVE", "editions"),
        ("sell_cost", True, "sell_cost"),
        ("sell_cost", -1, "sell_cost"),
    ):
        run = _shop_run()
        setattr(run.public.jokers[0], field, value)
        assert not can_sell_joker_exact(run, 0)
        with pytest.raises(HeadlessTransitionError, match=message):
            sell_joker_exact(run, 0)


def test_env_r3_exact_sale_rejects_inexact_index_and_money():
    run = _shop_run()
    for index in (True, -1, 1):
        assert not can_sell_joker_exact(run, index)

    run.public.money = True
    assert not can_sell_joker_exact(run, 0)
    with pytest.raises(HeadlessTransitionError, match="integer money"):
        sell_joker_exact(run, 0)


def test_env_r3_exact_sale_rejects_non_run_input():
    assert not can_sell_joker_exact(object(), 0)
    with pytest.raises(TypeError, match="HeadlessRunState"):
        sell_joker_exact(object(), 0)


def test_env_r3_shop_backend_masks_and_executes_only_exact_joker_sales():
    first = FlatMultJoker()
    first.sell_cost = 2
    first.live_id = 10
    second = FlatMultJoker()
    second.sell_cost = 4
    second.live_id = 20
    run = _shop_run(first)
    run.public.jokers.append(second)
    run.joker_order_state = None
    run = HeadlessRunState(public=run.public, seed="SELL-MASK")
    action = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    engine = ShopTransitionEngine()

    assert action in engine.legal_actions(run)
    result = engine.step(run, action)

    assert result.public.money == 10
    assert len(result.public.jokers) == 1
    assert result.public.jokers[0].live_id == 20
    result.require_joker_order_state()
    assert [joker.live_id for joker in result.joker_order_state.creation_order] == [20]
    assert [joker.live_id for joker in result.joker_order_state.physical_order] == [20]
    assert [joker.live_id for joker in run.public.jokers] == [10, 20]


def test_env_r3_shop_backend_masks_resource_sensitive_sale():
    run = _shop_run(TroubadourJoker())
    action = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    engine = ShopTransitionEngine()

    assert action not in engine.legal_actions(run)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(run, action)


def test_env_r3_exact_juggler_sale_applies_hand_size_inverse_once():
    run = _shop_run(JugglerJoker())
    run.public.hand_size = 9
    action = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    engine = ShopTransitionEngine()

    assert action in engine.legal_actions(run)
    result = engine.step(run, action)

    assert run.public.hand_size == 9
    assert len(run.public.jokers) == 1
    assert result.public.hand_size == 8
    assert result.public.jokers == []
    assert result.public.money == 10


@pytest.mark.parametrize("hand_size", [True, 0, -1])
def test_env_r3_juggler_sale_requires_exact_positive_hand_size(hand_size):
    run = _shop_run(JugglerJoker())
    run.public.hand_size = hand_size

    assert not can_sell_joker_exact(run, 0)
    with pytest.raises(HeadlessTransitionError, match="positive hand size"):
        sell_joker_exact(run, 0)


def test_env_r3_exact_drunkard_sale_applies_persistent_discard_inverse_once():
    run = _shop_run(DrunkardJoker())
    run.public.round_reset_discards_observed = True
    run.public.round_reset_discards = 4
    run.public.discards_remaining = 2
    action = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    engine = ShopTransitionEngine()

    assert action in engine.legal_actions(run)
    result = engine.step(run, action)

    assert run.public.round_reset_discards == 4
    assert run.public.discards_remaining == 2
    assert result.public.round_reset_discards == 3
    assert result.public.discards_remaining == 2
    assert result.public.jokers == []
    assert result.public.money == 10


def test_env_r3_exact_golden_joker_sale_is_inventory_only():
    run = _shop_run(GoldenJoker())
    action = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    engine = ShopTransitionEngine()

    assert action in engine.legal_actions(run)
    result = engine.step(run, action)

    assert run.public.jokers and type(run.public.jokers[0]) is GoldenJoker
    assert result.public.jokers == []
    assert result.public.money == 10


def test_env_r3_exact_bull_sale_is_inventory_only():
    run = _shop_run(BullJoker())
    action = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    engine = ShopTransitionEngine()

    assert action in engine.legal_actions(run)
    result = engine.step(run, action)

    assert run.public.jokers and type(run.public.jokers[0]) is BullJoker
    assert result.public.jokers == []
    assert result.public.money == 10


@pytest.mark.parametrize(
    ("observed", "round_reset_discards", "message"),
    [
        (False, 4, "authoritative"),
        (True, True, "positive"),
        (True, 0, "positive"),
        (True, -1, "positive"),
    ],
)
def test_env_r3_drunkard_sale_requires_exact_persistent_discard_state(
    observed,
    round_reset_discards,
    message,
):
    run = _shop_run(DrunkardJoker())
    run.public.round_reset_discards_observed = observed
    run.public.round_reset_discards = round_reset_discards

    assert not can_sell_joker_exact(run, 0)
    with pytest.raises(HeadlessTransitionError, match=message):
        sell_joker_exact(run, 0)
