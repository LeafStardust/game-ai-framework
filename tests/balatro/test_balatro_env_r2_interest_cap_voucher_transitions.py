import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.actions import EnvAction
from games.balatro.env.round_end import cash_out_baseline_ordinary_blind
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.state import BalatroState


def _voucher(key: str, *, price: int = 10) -> GeneratedShopVoucherItem:
    return GeneratedShopVoucherItem(center_key=key, base_cost=10, price=price)


def _shop_run(*, money=30, vouchers=(), cap=25, cap_observed=False) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = money
    state.vouchers_observed = True
    state.vouchers = list(vouchers)
    state.interest_cap = cap
    state.interest_cap_observed = cap_observed
    state.shop_discount_percent_observed = True
    state.shop_discount_percent = 0
    return HeadlessRunState(public=state, seed="INTEREST-TRANSITION")


def _buy_voucher(slot: int = 0) -> EnvAction:
    return EnvAction.from_alias("BUY_VOUCHER", {"slot": slot})


def test_env_r2_seed_money_is_training_legal_when_exact_and_affordable():
    run = _shop_run(money=10)
    run.public.shop_vouchers = [_voucher("v_seed_money", price=10)]

    assert _buy_voucher() in ShopTransitionEngine().legal_actions(run)


def test_env_r2_seed_money_action_debits_and_updates_cap_without_rng():
    run = _shop_run(money=30)
    run.public.shop_vouchers = [_voucher("v_seed_money", price=10)]
    before_rng = run.rng_snapshot()

    result = ShopTransitionEngine().step(run, _buy_voucher())

    assert result.public.money == 20
    assert result.public.vouchers == ["v_seed_money"]
    assert result.public.interest_cap_observed is True
    assert result.public.interest_cap == 50
    assert result.public.shop_vouchers == []
    assert result.rng_snapshot() == before_rng
    assert run.public.money == 30
    assert run.public.vouchers == []
    assert run.public.interest_cap == 25
    assert run.rng_snapshot() == before_rng


def test_env_r2_interest_voucher_action_disappears_when_unaffordable():
    run = _shop_run(money=9)
    run.public.shop_vouchers = [_voucher("v_seed_money", price=10)]

    assert _buy_voucher() not in ShopTransitionEngine().legal_actions(run)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        ShopTransitionEngine().step(run, _buy_voucher())


def test_env_r2_money_tree_is_hidden_before_seed_and_legal_after_seed():
    missing = _shop_run()
    missing.public.shop_vouchers = [_voucher("v_money_tree")]
    assert _buy_voucher() not in ShopTransitionEngine().legal_actions(missing)

    owned_seed = _shop_run(vouchers=("v_seed_money",), cap=25, cap_observed=False)
    owned_seed.public.shop_vouchers = [_voucher("v_money_tree")]
    assert _buy_voucher() in ShopTransitionEngine().legal_actions(owned_seed)

    result = ShopTransitionEngine().step(owned_seed, _buy_voucher())
    assert result.public.vouchers == ["v_seed_money", "v_money_tree"]
    assert result.public.interest_cap_observed is True
    assert result.public.interest_cap == 100


def test_env_r2_money_tree_action_rejects_explicit_stale_seed_cap():
    stale = _shop_run(vouchers=("v_seed_money",), cap=25, cap_observed=True)
    stale.public.shop_vouchers = [_voucher("v_money_tree")]

    assert _buy_voucher() not in ShopTransitionEngine().legal_actions(stale)


def test_env_r2_interest_voucher_purchase_composes_with_exact_cashout_interest():
    run = _shop_run(money=110)
    run.public.shop_vouchers = [_voucher("v_seed_money", price=10)]
    purchased = ShopTransitionEngine().step(run, _buy_voucher())

    purchased.public.phase = "ROUND_EVAL"
    purchased.public.shop_active = False
    purchased.public.score = 100
    purchased.public.hands_remaining = 0
    purchased.public.blind = Blind(BlindType.SMALL, requirement=100, reward=0)
    purchased.public.owned_deck = list(purchased.public.deck)
    purchased.draw_pile = list(purchased.public.deck)

    result = cash_out_baseline_ordinary_blind(purchased)

    # Purchase leaves $100; Seed Money raises the cap to $50, so cashout pays $10.
    assert result.public.money == 110
    assert result.public.interest_cap == 50
    assert result.public.vouchers == ["v_seed_money"]


def test_env_r2_unsupported_economy_voucher_remains_absent_from_training_actions():
    run = _shop_run()
    run.public.shop_vouchers = [_voucher("v_overstock_norm")]

    assert _buy_voucher() not in ShopTransitionEngine().legal_actions(run)
