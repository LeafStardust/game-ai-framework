from dataclasses import dataclass

import pytest

from games.balatro.env import EnvAction
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.jokers.flat_mult import FlatMultJoker
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


def _base_joker(*, cost=5, edition=None):
    joker = FlatMultJoker()
    joker.label = "Joker"
    joker.cost = cost
    if edition is not None:
        joker.edition = edition
    return joker


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

    assert EnvAction.from_alias("BUY_CONSUMABLE", {"slot": 0}) in legal
    assert EnvAction.from_alias("END_SHOP") in legal
    assert EnvAction.from_alias("BUY_JOKER", {"slot": 0}) not in legal
    assert EnvAction.from_alias("BUY_JOKER", {"slot": 1}) not in legal
    assert EnvAction.from_alias("BUY_VOUCHER", {"slot": 0}) not in legal
    assert EnvAction.from_alias("OPEN_PACK", {"slot": 0}) not in legal


def test_balatro_env_r1_buy_consumable_updates_exact_zone():
    run = HeadlessRunState(public=_shop_state(), seed=8)

    after_consumable = ShopTransitionEngine().step(
        run,
        EnvAction.from_alias("BUY_CONSUMABLE", {"slot": 0}),
    )

    assert run.public.money == 20
    assert run.public.consumables == []
    assert after_consumable.public.money == 17
    assert [item.label for item in after_consumable.public.consumables] == ["Tarot A"]
    assert after_consumable.public.shop_consumables == []


def test_balatro_env_r1_base_joker_acquisition_is_exact_and_isolated():
    state = _shop_state()
    state.shop_jokers = [_base_joker(), _Item("Unsupported Joker", 5)]
    run = HeadlessRunState(public=state, seed=9)
    engine = ShopTransitionEngine()

    legal = engine.legal_actions(run)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in legal
    assert EnvAction.from_alias("BUY_JOKER", {"slot": 1}) not in legal

    next_run = engine.step(run, action)

    assert run.public.money == 20
    assert run.public.jokers == []
    assert len(run.public.shop_jokers) == 2
    assert next_run.public.money == 15
    assert len(next_run.public.jokers) == 1
    assert type(next_run.public.jokers[0]) is FlatMultJoker
    assert next_run.public.jokers[0].mult == 4
    assert [item.label for item in next_run.public.shop_jokers] == ["Unsupported Joker"]


def test_balatro_env_r1_joker_editions_remain_fail_closed():
    state = _shop_state()
    state.shop_jokers = [_base_joker(edition="Negative")]
    run = HeadlessRunState(public=state, seed=10)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action not in engine.legal_actions(run)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition: BUY_JOKER"):
        engine.step(run, action)

    assert run.public.money == 20
    assert run.public.jokers == []
    assert len(run.public.shop_jokers) == 1


def test_balatro_env_r1_rejects_unsupported_acquisition_execution():
    run = HeadlessRunState(public=_shop_state(), seed=11)
    engine = ShopTransitionEngine()

    for alias in ("BUY_JOKER", "BUY_VOUCHER", "OPEN_PACK"):
        with pytest.raises(
            HeadlessTransitionError,
            match=rf"illegal shop transition: {alias}",
        ):
            engine.step(run, EnvAction.from_alias(alias, {"slot": 0}))

    assert run.public.money == 20
    assert run.public.jokers == []
    assert run.public.vouchers == []
    assert [item.label for item in run.public.shop_jokers] == ["Joker A", "Joker B"]
    assert [item.label for item in run.public.shop_vouchers] == ["Voucher A"]
    assert [item.label for item in run.public.shop_boosters] == ["Pack A"]


def test_balatro_env_r1_end_shop_clears_offers_and_transfers_phase():
    run = HeadlessRunState(public=_shop_state(), seed=12)
    next_run = ShopTransitionEngine().step(run, EnvAction.from_alias("END_SHOP"))

    assert next_run.public.phase == "BLIND_SELECT"
    assert next_run.public.shop_active is False
    assert next_run.public.shop_jokers == []
    assert next_run.public.shop_consumables == []
    assert next_run.public.shop_vouchers == []
    assert next_run.public.shop_boosters == []
    assert ShopTransitionEngine().legal_actions(next_run) == ()


def test_balatro_env_r1_rejects_unaffordable_or_invalid_shop_action():
    run = HeadlessRunState(public=_shop_state(money=2), seed=13)
    engine = ShopTransitionEngine()

    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(run, EnvAction.from_alias("BUY_CONSUMABLE", {"slot": 0}))

    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(run, EnvAction.from_alias("BUY_CONSUMABLE", {"slot": 99}))
