from dataclasses import dataclass

import pytest

from games.balatro.env import EnvAction
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.state import BalatroState


@dataclass
class _Item:
    label: str
    price: int


def _shop_state(*, money=20):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = money
    state.shop_jokers = [_Item("Joker A", 5), _Item("Joker B", 50)]
    state.shop_consumables = [_Item("Tarot A", 3)]
    state.shop_vouchers = [_Item("Voucher A", 10)]
    state.shop_boosters = [_Item("Pack A", 4)]
    return state


def test_balatro_env_r1_state_rejects_non_red_white_surface():
    state = _shop_state()
    state.deck_name = "BLUE"
    with pytest.raises(HeadlessTransitionError, match="Red Deck"):
        HeadlessRunState(public=state, seed=1)

    state = _shop_state()
    state.stake_name = "RED"
    with pytest.raises(HeadlessTransitionError, match="White Stake"):
        HeadlessRunState(public=state, seed=1)


def test_balatro_env_r1_shop_legality_is_exact_for_deterministic_subset():
    run = HeadlessRunState(public=_shop_state(), seed="shop-seed")
    legal = ShopTransitionEngine().legal_actions(run)

    assert EnvAction.from_alias("BUY_JOKER", {"slot": 0}) in legal
    assert EnvAction.from_alias("BUY_CONSUMABLE", {"slot": 0}) in legal
    assert EnvAction.from_alias("BUY_VOUCHER", {"slot": 0}) in legal
    assert EnvAction.from_alias("END_SHOP") in legal
    assert EnvAction.from_alias("BUY_JOKER", {"slot": 1}) not in legal
    assert all(action.alias != "OPEN_PACK" for action in legal)


def test_balatro_env_r1_buy_joker_isolated_and_deterministic():
    run = HeadlessRunState(public=_shop_state(), seed=7)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    next_run = ShopTransitionEngine().step(run, action)

    assert run.public.money == 20
    assert len(run.public.jokers) == 0
    assert len(run.public.shop_jokers) == 2
    assert next_run.public.money == 15
    assert [item.label for item in next_run.public.jokers] == ["Joker A"]
    assert [item.label for item in next_run.public.shop_jokers] == ["Joker B"]


def test_balatro_env_r1_buy_consumable_and_voucher_update_exact_zones():
    engine = ShopTransitionEngine()
    run = HeadlessRunState(public=_shop_state(), seed=8)

    after_consumable = engine.step(
        run,
        EnvAction.from_alias("BUY_CONSUMABLE", {"slot": 0}),
    )
    after_voucher = engine.step(
        after_consumable,
        EnvAction.from_alias("BUY_VOUCHER", {"slot": 0}),
    )

    assert after_consumable.public.money == 17
    assert [item.label for item in after_consumable.public.consumables] == ["Tarot A"]
    assert after_voucher.public.money == 7
    assert [item.label for item in after_voucher.public.vouchers] == ["Voucher A"]
    assert after_voucher.public.shop_vouchers == []


def test_balatro_env_r1_end_shop_clears_offers_and_transfers_phase():
    run = HeadlessRunState(public=_shop_state(), seed=9)
    next_run = ShopTransitionEngine().step(run, EnvAction.from_alias("END_SHOP"))

    assert next_run.public.phase == "BLIND_SELECT"
    assert next_run.public.shop_active is False
    assert next_run.public.shop_jokers == []
    assert next_run.public.shop_consumables == []
    assert next_run.public.shop_vouchers == []
    assert next_run.public.shop_boosters == []
    assert ShopTransitionEngine().legal_actions(next_run) == ()


def test_balatro_env_r1_rejects_unaffordable_or_invalid_shop_action():
    run = HeadlessRunState(public=_shop_state(money=2), seed=10)
    engine = ShopTransitionEngine()

    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(run, EnvAction.from_alias("BUY_JOKER", {"slot": 0}))

    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(run, EnvAction.from_alias("BUY_JOKER", {"slot": 99}))
