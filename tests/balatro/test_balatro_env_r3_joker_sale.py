import pytest

from games.balatro.env.joker_sale import (
    can_sell_joker_exact,
    sell_joker_exact,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.juggler import JugglerJoker
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
    run = _shop_run(JugglerJoker())
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
