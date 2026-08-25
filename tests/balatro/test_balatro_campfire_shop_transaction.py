from copy import deepcopy
from types import SimpleNamespace

from games.balatro.jokers.campfire import CampfireJoker
from games.balatro.planets import PLANET_CARDS
from games.balatro.shop_transaction_policy import (
    _campfire_fuel_candidate,
    _fuel_inventory_index,
)


def _state(*, money=43, x_mult=1.25, consumables=()):
    campfire = CampfireJoker()
    campfire.x_mult = x_mult
    pluto = deepcopy(PLANET_CARDS["PLUTO"])
    pluto.cost = 3
    pluto.discovered = True
    return SimpleNamespace(
        ante=6,
        money=money,
        jokers=[campfire],
        shop_consumables=[pluto],
        consumables=list(consumables),
        consumable_slots=2,
        hand_levels={},
        hand_play_counts={},
        vouchers=[],
    )


def test_weak_campfire_uses_visible_cheap_planet_as_fuel():
    state = _state()

    assert _campfire_fuel_candidate(state) is state.shop_consumables[0]


def test_campfire_fuel_preserves_late_cash_reserve():
    assert _campfire_fuel_candidate(_state(money=22)) is None


def test_pending_fuel_sale_targets_new_duplicate_not_existing_inventory():
    existing = deepcopy(PLANET_CARDS["PLUTO"])
    bought = deepcopy(PLANET_CARDS["PLUTO"])
    state = _state(consumables=(existing, bought))

    assert _fuel_inventory_index(
        state,
        {"label": "pluto", "existing_count": 1},
    ) == 1
