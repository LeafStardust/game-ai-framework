import pytest

from games.balatro.env.joker_removal import destroy_inventory_only_joker_exact
from games.balatro.env.joker_sale import can_sell_joker_exact, sell_joker_exact
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.campfire import CampfireJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.state import BalatroState


def _shop_run(*jokers):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = 7
    state.jokers = list(jokers)
    for index, joker in enumerate(jokers):
        joker.live_id = index
        joker.sell_cost = 3
    return HeadlessRunState(public=state, seed="CAMPFIRE-SALE")


@pytest.mark.parametrize("debuffed, expected", [(False, 1.5), (True, 1.0)])
def test_paid_joker_sales_grow_retained_campfire_once_each(debuffed, expected):
    campfire = CampfireJoker()
    campfire.debuffed = debuffed
    run = _shop_run(FlatMultJoker(), campfire, FlatMultJoker())
    rng = run.rng_snapshot()

    first = sell_joker_exact(run, 0)
    second = sell_joker_exact(first, 1)

    assert first.public.money == 10
    assert second.public.money == 13
    assert first.public.jokers[0].x_mult == (1.0 if debuffed else 1.25)
    assert second.public.jokers[0].x_mult == expected
    assert first.rng_snapshot() == second.rng_snapshot() == rng
    assert campfire.x_mult == 1.0
    assert run.public.money == 7


def test_campfire_does_not_grow_when_another_joker_is_destroyed():
    run = _shop_run(FlatMultJoker(), CampfireJoker())

    result = destroy_inventory_only_joker_exact(run, 0)

    assert result.public.jokers[0].x_mult == 1.0
    assert result.public.money == 7


def test_joker_sale_masks_inexact_campfire_growth():
    campfire = CampfireJoker()
    campfire.x_mult = 1.1
    run = _shop_run(FlatMultJoker(), campfire)
    rng = run.rng_snapshot()

    assert not can_sell_joker_exact(run, 0)
    with pytest.raises(HeadlessTransitionError, match="exact retained Campfire state"):
        sell_joker_exact(run, 0)

    assert run.public.money == 7
    assert run.public.jokers[1] is campfire
    assert campfire.x_mult == 1.1
    assert run.rng_snapshot() == rng
