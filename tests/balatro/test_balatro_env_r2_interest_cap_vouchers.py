import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.interest_cap_voucher_redemption import (
    interest_cap_voucher_redemption_is_exact,
    redeem_exact_interest_cap_voucher,
)
from games.balatro.env.round_end import (
    baseline_interest_dollars,
    cash_out_baseline_ordinary_blind,
)
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.env.voucher_capabilities import (
    expected_interest_cap_for_vouchers,
    interest_cap_vouchers_are_exact,
)
from games.balatro.state import BalatroState


def _voucher(key: str, price: int = 10) -> GeneratedShopVoucherItem:
    return GeneratedShopVoucherItem(center_key=key, base_cost=10, price=price)


def _shop_run(*, vouchers=(), cap=25, cap_observed=False, money=30):
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
    return HeadlessRunState(public=state, seed="INTEREST-VOUCHER")


def _cleared_run(*, money, vouchers=(), cap=25, cap_observed=False):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "ROUND_EVAL"
    state.money = money
    state.score = 100
    state.hands_remaining = 0
    state.blind = Blind(BlindType.SMALL, requirement=100, reward=0)
    state.owned_deck = list(state.deck)
    state.vouchers_observed = True
    state.vouchers = list(vouchers)
    state.interest_cap = cap
    state.interest_cap_observed = cap_observed
    state.shop_discount_percent_observed = True
    state.shop_discount_percent = 0
    run = HeadlessRunState(public=state, seed="INTEREST-CASHOUT")
    run.draw_pile = list(state.deck)
    return run


def test_env_r2_interest_cap_expected_values_and_progression():
    base = _shop_run()
    assert expected_interest_cap_for_vouchers(base.public) == 25
    assert interest_cap_vouchers_are_exact(base.public)

    seed = _shop_run(vouchers=("v_seed_money",), cap=50, cap_observed=True)
    assert expected_interest_cap_for_vouchers(seed.public) == 50
    assert interest_cap_vouchers_are_exact(seed.public)

    tree = _shop_run(
        vouchers=("v_seed_money", "v_money_tree"),
        cap=100,
        cap_observed=True,
    )
    assert expected_interest_cap_for_vouchers(tree.public) == 100
    assert interest_cap_vouchers_are_exact(tree.public)

    invalid = _shop_run(vouchers=("v_money_tree",), cap=100, cap_observed=True)
    assert expected_interest_cap_for_vouchers(invalid.public) is None
    assert not interest_cap_vouchers_are_exact(invalid.public)


def test_env_r2_interest_modifier_requires_observed_matching_cap():
    missing = _shop_run(vouchers=("v_seed_money",), cap=50, cap_observed=False)
    stale = _shop_run(vouchers=("v_seed_money",), cap=25, cap_observed=True)

    assert not interest_cap_vouchers_are_exact(missing.public)
    assert not interest_cap_vouchers_are_exact(stale.public)


def test_env_r2_seed_money_redemption_sets_cap_without_rng():
    run = _shop_run()
    run.public.shop_vouchers = [_voucher("v_seed_money")]
    before_rng = run.rng_snapshot()

    assert interest_cap_voucher_redemption_is_exact(run, 0)
    result = redeem_exact_interest_cap_voucher(run, 0)

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


def test_env_r2_money_tree_requires_seed_and_exact_current_cap():
    missing = _shop_run()
    missing.public.shop_vouchers = [_voucher("v_money_tree")]
    assert not interest_cap_voucher_redemption_is_exact(missing, 0)
    with pytest.raises(HeadlessTransitionError, match="requires v_seed_money"):
        redeem_exact_interest_cap_voucher(missing, 0)

    stale = _shop_run(
        vouchers=("v_seed_money",),
        cap=25,
        cap_observed=True,
    )
    stale.public.shop_vouchers = [_voucher("v_money_tree")]
    assert not interest_cap_voucher_redemption_is_exact(stale, 0)

    run = _shop_run(
        vouchers=("v_seed_money",),
        cap=50,
        cap_observed=True,
    )
    run.public.shop_vouchers = [_voucher("v_money_tree")]
    result = redeem_exact_interest_cap_voucher(run, 0)
    assert result.public.vouchers == ["v_seed_money", "v_money_tree"]
    assert result.public.interest_cap == 100


def test_env_r2_interest_cap_changes_cashout_ceiling_exactly():
    assert baseline_interest_dollars(100, 25) == 5
    assert baseline_interest_dollars(100, 50) == 10
    assert baseline_interest_dollars(100, 100) == 20

    base = cash_out_baseline_ordinary_blind(_cleared_run(money=100))
    seed = cash_out_baseline_ordinary_blind(
        _cleared_run(
            money=100,
            vouchers=("v_seed_money",),
            cap=50,
            cap_observed=True,
        )
    )
    tree = cash_out_baseline_ordinary_blind(
        _cleared_run(
            money=100,
            vouchers=("v_seed_money", "v_money_tree"),
            cap=100,
            cap_observed=True,
        )
    )

    assert base.public.money == 105
    assert seed.public.money == 110
    assert tree.public.money == 120
    assert seed.public.interest_cap == 50
    assert tree.public.interest_cap == 100


def test_env_r2_cashout_rejects_unobserved_or_stale_owned_interest_cap():
    missing = _cleared_run(
        money=100,
        vouchers=("v_seed_money",),
        cap=50,
        cap_observed=False,
    )
    with pytest.raises(HeadlessTransitionError, match="interest-cap"):
        cash_out_baseline_ordinary_blind(missing)

    stale = _cleared_run(
        money=100,
        vouchers=("v_seed_money",),
        cap=25,
        cap_observed=True,
    )
    with pytest.raises(HeadlessTransitionError, match="interest-cap"):
        cash_out_baseline_ordinary_blind(stale)


def test_env_r2_interest_redemption_rejects_unaffordable_wrong_phase_and_bad_metadata():
    unaffordable = _shop_run(money=9)
    unaffordable.public.shop_vouchers = [_voucher("v_seed_money")]
    assert not interest_cap_voucher_redemption_is_exact(unaffordable, 0)

    wrong_phase = _shop_run()
    wrong_phase.public.phase = "BLIND_SELECT"
    wrong_phase.public.shop_vouchers = [_voucher("v_seed_money")]
    assert not interest_cap_voucher_redemption_is_exact(wrong_phase, 0)

    legacy = _shop_run()
    legacy.public.shop_vouchers = [object()]
    assert not interest_cap_voucher_redemption_is_exact(legacy, 0)
