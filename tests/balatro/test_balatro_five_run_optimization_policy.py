from __future__ import annotations

from types import SimpleNamespace

from games.balatro.actions import BUY_AND_USE_CONSUMABLE
from games.balatro.live.consumable_timing_base import LiveConsumableTimingPolicy
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.state import BalatroState
from games.balatro.strategy import GOLD, SILVER
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_conditional_relationships import conditional_joker_relationship


class JokerStencil:
    pass


class RocketJoker:
    pass


class ToTheMoonJoker:
    pass


class DeviousJoker:
    pass


class FourFingersJoker:
    cost = 7


class BannerJoker:
    eternal = False
    edition = None


class PerkeoJoker:
    pass


def test_joker_stencil_is_not_gold() -> None:
    definition = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["joker_stencil"]
    assert definition.relationship_for(JokerStencil(), kind="JOKER") == SILVER


def test_cash_growth_is_silver_solo_and_gold_as_pair() -> None:
    definition = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["cash_growth"]
    rocket = RocketJoker()
    moon = ToTheMoonJoker()
    assert definition.relationship_for(rocket, kind="JOKER") == SILVER
    assert definition.relationship_for(moon, kind="JOKER") == SILVER

    state = BalatroState()
    state.jokers = [rocket]
    assert conditional_joker_relationship(state, "cash_growth", moon) == GOLD

    state.jokers = [rocket, moon]
    assert conditional_joker_relationship(state, "cash_growth", rocket) == GOLD
    assert conditional_joker_relationship(state, "cash_growth", moon) == GOLD


def test_held_hermit_uses_at_twenty_or_more() -> None:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 33
    hermit = SimpleNamespace(name="The Hermit")
    state.consumables = [hermit]

    recommendation = LiveConsumableTimingPolicy().recommend(state, hermit)
    assert recommendation.should_use
    assert recommendation.immediate_gain == 20.0


def test_profitable_shop_hermit_is_bought_and_used() -> None:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 20
    hermit = SimpleNamespace(name="The Hermit", label="The Hermit", cost=3)
    state.shop_consumables = [hermit]

    decision = BuildAwareShopArbiter().decide(
        state,
        [],
        reroll_cost=5,
    )
    assert decision.action.name == BUY_AND_USE_CONSUMABLE
    assert decision.action.target is hermit


def test_devious_four_fingers_can_replace_weak_filler() -> None:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 20
    state.joker_slots = 2
    state.jokers = [DeviousJoker(), BannerJoker()]
    four_fingers = FourFingersJoker()
    state.shop_jokers = [four_fingers]

    decision = BuildAwareShopArbiter().decide(
        state,
        [],
        reroll_cost=5,
    )
    assert decision.action.name == "SELL_JOKER"
    assert decision.action.target == 1


def test_perkeo_does_not_end_shop_without_a_safe_seed() -> None:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 10
    state.jokers = [PerkeoJoker()]
    seed = SimpleNamespace(name="The Emperor", label="The Emperor", cost=3)
    state.shop_consumables = [seed]

    decision = BuildAwareShopArbiter().decide(
        state,
        [],
        reroll_cost=5,
    )
    assert decision.action.name == "BUY_CONSUMABLE"
    assert decision.action.target is seed
