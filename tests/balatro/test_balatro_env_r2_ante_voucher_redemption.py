import pytest

from games.balatro.env.ante_voucher_redemption import (
    ante_voucher_redemption_is_exact,
    redeem_exact_ante_voucher,
)
from games.balatro.env.blind_progression import BlindProgressionState
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run(
    key: str,
    *,
    price: int = 10,
    blind_ante: int | None = 2,
) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = 20
    state.ante = 2
    state.hands_remaining = 4
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.discards_remaining = 3
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    state.vouchers_observed = True
    state.shop_vouchers = [
        GeneratedShopVoucherItem(center_key=key, base_cost=10, price=price)
    ]
    progression = (
        None
        if blind_ante is None
        else BlindProgressionState(blind_ante=blind_ante)
    )
    return HeadlessRunState(
        public=state,
        seed="ANTE-VOUCHER",
        blind_progression_state=progression,
    )


def test_env_r2_hieroglyph_redeems_exact_ante_and_hand_allowances():
    run = _run("v_hieroglyph")
    before_rng = run.rng_snapshot()

    result = redeem_exact_ante_voucher(run, slot=0)

    assert result.public.money == 10
    assert result.public.ante == 1
    assert result.public.round_reset_hands == 3
    assert result.public.hands_remaining == 3
    assert result.public.round_reset_discards == 3
    assert result.public.discards_remaining == 3
    assert result.public.vouchers == ["v_hieroglyph"]
    assert result.public.vouchers_observed is True
    assert result.public.shop_vouchers == []
    assert result.require_blind_progression_state().blind_ante == 1
    assert result.rng_snapshot() == before_rng

    # Inputs remain isolated, including the retained private progression owner.
    assert run.public.money == 20
    assert run.public.ante == 2
    assert run.public.round_reset_hands == 4
    assert run.public.hands_remaining == 4
    assert run.public.vouchers == []
    assert run.require_blind_progression_state().blind_ante == 2


def test_env_r2_petroglyph_requires_hieroglyph_and_reduces_discards():
    run = _run("v_petroglyph")

    assert not ante_voucher_redemption_is_exact(run, slot=0)
    with pytest.raises(HeadlessTransitionError, match="requires Hieroglyph"):
        redeem_exact_ante_voucher(run, slot=0)

    run.public.vouchers = ["v_hieroglyph"]
    result = redeem_exact_ante_voucher(run, slot=0)

    assert result.public.ante == 1
    assert result.public.round_reset_discards == 2
    assert result.public.discards_remaining == 2
    assert result.public.round_reset_hands == 4
    assert result.public.hands_remaining == 4
    assert result.public.vouchers == ["v_hieroglyph", "v_petroglyph"]
    assert result.require_blind_progression_state().blind_ante == 1


def test_env_r2_ante_vouchers_support_zero_and_negative_ante_exactly():
    run = _run("v_hieroglyph", blind_ante=0)
    run.public.ante = 0

    result = redeem_exact_ante_voucher(run, slot=0)

    assert result.public.ante == -1
    assert result.require_blind_progression_state().blind_ante == -1


def test_env_r2_ante_voucher_requires_retained_private_progression():
    run = _run("v_hieroglyph", blind_ante=None)
    before_rng = run.rng_snapshot()

    assert not ante_voucher_redemption_is_exact(run, slot=0)
    with pytest.raises(HeadlessTransitionError, match="progression state is unavailable"):
        redeem_exact_ante_voucher(run, slot=0)

    assert run.public.money == 20
    assert run.public.ante == 2
    assert run.rng_snapshot() == before_rng


def test_env_r2_ante_voucher_rejects_stale_private_blind_ante():
    run = _run("v_hieroglyph", blind_ante=1)
    before_rng = run.rng_snapshot()

    assert not ante_voucher_redemption_is_exact(run, slot=0)
    with pytest.raises(HeadlessTransitionError, match="stale relative"):
        redeem_exact_ante_voucher(run, slot=0)

    assert run.public.money == 20
    assert run.public.ante == 2
    assert run.rng_snapshot() == before_rng


def test_env_r2_ante_voucher_fails_closed_on_unobserved_or_irreducible_allowance():
    run = _run("v_hieroglyph")
    run.public.round_reset_hands_observed = False
    assert not ante_voucher_redemption_is_exact(run, slot=0)

    run = _run("v_hieroglyph")
    run.public.round_reset_hands = 0
    assert not ante_voucher_redemption_is_exact(run, slot=0)

    run = _run("v_hieroglyph")
    run.public.hands_remaining = 0
    assert not ante_voucher_redemption_is_exact(run, slot=0)

    run = _run("v_petroglyph")
    run.public.vouchers = ["v_hieroglyph"]
    run.public.round_reset_discards_observed = False
    assert not ante_voucher_redemption_is_exact(run, slot=0)

    run = _run("v_petroglyph")
    run.public.vouchers = ["v_hieroglyph"]
    run.public.round_reset_discards = 0
    assert not ante_voucher_redemption_is_exact(run, slot=0)

    run = _run("v_petroglyph")
    run.public.vouchers = ["v_hieroglyph"]
    run.public.discards_remaining = 0
    assert not ante_voucher_redemption_is_exact(run, slot=0)


def test_env_r2_ante_voucher_rejects_wrong_phase_affordability_and_duplicate():
    run = _run("v_hieroglyph")
    run.public.phase = "BLIND_SELECT"
    assert not ante_voucher_redemption_is_exact(run, slot=0)

    run = _run("v_hieroglyph", price=21)
    assert not ante_voucher_redemption_is_exact(run, slot=0)

    run = _run("v_hieroglyph")
    run.public.vouchers = ["v_hieroglyph"]
    assert not ante_voucher_redemption_is_exact(run, slot=0)
