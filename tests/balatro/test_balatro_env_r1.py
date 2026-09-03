from dataclasses import dataclass

import pytest

from games.balatro.env import EnvAction
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.jokers.abstract_joker import AbstractJoker
from games.balatro.jokers.acrobat import AcrobatJoker
from games.balatro.jokers.banner import BannerJoker
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.blackboard import BlackboardJoker
from games.balatro.jokers.blue_joker import BlueJoker
from games.balatro.jokers.drunkard import DrunkardJoker
from games.balatro.jokers.even_steven import EvenStevenJoker
from games.balatro.jokers.fibonacci import FibonacciJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.juggler import JugglerJoker
from games.balatro.jokers.mystic_summit import MysticSummitJoker
from games.balatro.jokers.odd_todd import OddToddJoker
from games.balatro.jokers.raised_fist import RaisedFistJoker
from games.balatro.jokers.scholar import ScholarJoker
from games.balatro.jokers.smiley_face import SmileyFaceJoker
from games.balatro.jokers.stuntman import StuntmanJoker
from games.balatro.jokers.troubadour import TroubadourJoker
from games.balatro.state import BalatroState


@dataclass
class _Item:
    label: str
    price: object


@dataclass
class _PricelessItem:
    label: str


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


def _modeled_joker(joker_type=FlatMultJoker, *, cost=5, edition=None):
    joker = joker_type()
    joker.label = joker_type.__name__
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


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("money", "20", "money must be an exact integer"),
        ("money", True, "money must be an exact integer"),
        ("joker_slots", 5.0, "joker_slots must be an exact integer"),
        ("joker_slots", -1, "joker_slots cannot be negative"),
        ("consumable_slots", "2", "consumable_slots must be an exact integer"),
        ("consumable_slots", -1, "consumable_slots cannot be negative"),
    ),
)
def test_balatro_env_r1_state_rejects_inexact_shop_numeric_state(field, value, message):
    state = _shop_state()
    setattr(state, field, value)

    with pytest.raises(HeadlessTransitionError, match=message):
        HeadlessRunState(public=state, seed=2)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    (
        ({"reroll_cost": 5.0}, "reroll_cost must be an exact integer"),
        ({"reroll_cost": -1}, "reroll_cost cannot be negative"),
        ({"skips": True}, "skips must be an exact integer"),
        ({"skips": -1}, "skips cannot be negative"),
    ),
)
def test_balatro_env_r1_state_rejects_inexact_environment_counters(kwargs, message):
    with pytest.raises(HeadlessTransitionError, match=message):
        HeadlessRunState(public=_shop_state(), seed=3, **kwargs)


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


@pytest.mark.parametrize(
    "joker_type",
    (
        FlatMultJoker,
        AbstractJoker,
        AcrobatJoker,
        BannerJoker,
        BaronJoker,
        BlackboardJoker,
        BlueJoker,
        EvenStevenJoker,
        FibonacciJoker,
        MysticSummitJoker,
        OddToddJoker,
        RaisedFistJoker,
        ScholarJoker,
        SmileyFaceJoker,
        JugglerJoker,
        StuntmanJoker,
    ),
)
def test_balatro_env_r1_audited_joker_acquisition_is_exact_and_isolated(joker_type):
    state = _shop_state()
    state.shop_jokers = [_modeled_joker(joker_type), _Item("Unsupported Joker", 5)]
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
    assert type(next_run.public.jokers[0]) is joker_type
    assert [item.label for item in next_run.public.shop_jokers] == ["Unsupported Joker"]


def test_balatro_env_r1_base_joker_keeps_modeled_scoring_state():
    state = _shop_state()
    state.shop_jokers = [_modeled_joker(FlatMultJoker)]
    run = HeadlessRunState(public=state, seed=10)

    next_run = ShopTransitionEngine().step(
        run,
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
    )

    assert type(next_run.public.jokers[0]) is FlatMultJoker
    assert next_run.public.jokers[0].mult == 4


@pytest.mark.parametrize(
    ("joker_type", "expected_hand_size"),
    (
        (JugglerJoker, 9),
        (StuntmanJoker, 6),
    ),
)
def test_balatro_env_r1_hand_size_joker_acquisition_updates_capacity_once(
    joker_type,
    expected_hand_size,
):
    state = _shop_state()
    state.shop_jokers = [_modeled_joker(joker_type)]
    state.hand_size = 8
    run = HeadlessRunState(public=state, seed=11)

    next_run = ShopTransitionEngine().step(
        run,
        EnvAction.from_alias("BUY_JOKER", {"slot": 0}),
    )

    assert run.public.hand_size == 8
    assert run.public.jokers == []
    assert next_run.public.hand_size == expected_hand_size
    assert len(next_run.public.jokers) == 1
    assert type(next_run.public.jokers[0]) is joker_type


def test_balatro_env_r1_unobserved_round_resource_joker_remains_fail_closed():
    state = _shop_state()
    state.shop_jokers = [_modeled_joker(DrunkardJoker)]
    run = HeadlessRunState(public=state, seed=12)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert state.round_reset_discards_observed is False
    assert action not in engine.legal_actions(run)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition: BUY_JOKER"):
        engine.step(run, action)

    assert run.public.money == 20
    assert run.public.jokers == []
    assert run.public.round_reset_discards == 0


def test_balatro_env_r1_troubadour_remains_fail_closed_without_next_round_hands_owner():
    state = _shop_state()
    state.shop_jokers = [_modeled_joker(TroubadourJoker)]
    state.hand_size = 8
    state.hands_remaining = 2
    run = HeadlessRunState(public=state, seed=13)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action not in engine.legal_actions(run)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition: BUY_JOKER"):
        engine.step(run, action)

    assert run.public.money == 20
    assert run.public.hand_size == 8
    assert run.public.hands_remaining == 2
    assert run.public.jokers == []


def test_balatro_env_r1_drunkard_updates_authoritative_next_round_discards_only():
    state = _shop_state()
    state.shop_jokers = [_modeled_joker(DrunkardJoker)]
    state.discards_remaining = 1
    state.round_reset_discards_observed = True
    state.round_reset_discards = 4
    run = HeadlessRunState(public=state, seed=14)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action in engine.legal_actions(run)
    next_run = engine.step(run, action)

    assert run.public.money == 20
    assert run.public.discards_remaining == 1
    assert run.public.round_reset_discards == 4
    assert run.public.jokers == []
    assert next_run.public.money == 15
    assert next_run.public.discards_remaining == 1
    assert next_run.public.round_reset_discards_observed is True
    assert next_run.public.round_reset_discards == 5
    assert len(next_run.public.jokers) == 1
    assert type(next_run.public.jokers[0]) is DrunkardJoker


def test_balatro_env_r1_joker_editions_remain_fail_closed():
    state = _shop_state()
    state.shop_jokers = [_modeled_joker(FlatMultJoker, edition="Negative")]
    run = HeadlessRunState(public=state, seed=15)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action not in engine.legal_actions(run)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition: BUY_JOKER"):
        engine.step(run, action)

    assert run.public.money == 20
    assert run.public.jokers == []
    assert len(run.public.shop_jokers) == 1


def test_balatro_env_r1_rejects_unsupported_acquisition_execution():
    run = HeadlessRunState(public=_shop_state(), seed=16)
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


def test_balatro_env_r1_affordability_rejects_inexact_prices():
    state = _shop_state()
    state.shop_consumables = [
        _Item("Negative", -1),
        _Item("Invalid", "not-a-price"),
        _Item("Numeric string", "3"),
        _Item("Integral float", 3.0),
        _Item("Fractional float", 3.9),
        _Item("Boolean", True),
        _PricelessItem("Missing"),
    ]
    run = HeadlessRunState(public=state, seed=17)
    engine = ShopTransitionEngine()
    legal = engine.legal_actions(run)

    assert EnvAction.from_alias("END_SHOP") in legal
    assert all(action.alias != "BUY_CONSUMABLE" for action in legal)

    for slot in range(len(state.shop_consumables)):
        with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
            engine.step(run, EnvAction.from_alias("BUY_CONSUMABLE", {"slot": slot}))

    assert run.public.money == 20
    assert run.public.consumables == []


def test_balatro_env_r1_end_shop_clears_offers_and_transfers_phase():
    run = HeadlessRunState(public=_shop_state(), seed=18)
    next_run = ShopTransitionEngine().step(run, EnvAction.from_alias("END_SHOP"))

    assert next_run.public.phase == "BLIND_SELECT"
    assert next_run.public.shop_active is False
    assert next_run.public.shop_jokers == []
    assert next_run.public.shop_consumables == []
    assert next_run.public.shop_vouchers == []
    assert next_run.public.shop_boosters == []
    assert ShopTransitionEngine().legal_actions(next_run) == ()


def test_balatro_env_r1_rejects_unaffordable_or_invalid_shop_action():
    run = HeadlessRunState(public=_shop_state(money=2), seed=19)
    engine = ShopTransitionEngine()

    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(run, EnvAction.from_alias("BUY_CONSUMABLE", {"slot": 0}))

    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(run, EnvAction.from_alias("BUY_CONSUMABLE", {"slot": 99}))
