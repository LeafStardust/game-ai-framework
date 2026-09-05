"""Exact internal redemption primitive for Hieroglyph / Petroglyph.

Vanilla redemption mutates both policy-visible run state (Ante and round
allowances) and private ``G.GAME.round_resets.blind_ante``. The generic
``HeadlessRunState`` now retains the existing canonical ``BlindProgressionState``
owner, so this shop primitive requires and updates that state directly rather
than accepting a parallel progression argument.
"""

from __future__ import annotations

from games.balatro.env.blind_progression import BlindProgressionState
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


EXACT_ANTE_VOUCHER_KEYS = frozenset({"v_hieroglyph", "v_petroglyph"})


def _validate_exact_redeem_boundary(
    run: HeadlessRunState,
    *,
    slot: int,
) -> tuple[GeneratedShopVoucherItem, str, BlindProgressionState]:
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if isinstance(slot, bool) or not isinstance(slot, int):
        raise HeadlessTransitionError("Voucher slot must be an exact integer")

    progression = run.require_blind_progression_state()
    state = run.public
    if state.phase != "SHOP" or state.shop_active is not True:
        raise HeadlessTransitionError("Ante Voucher redemption requires active SHOP")
    if slot < 0 or slot >= len(state.shop_vouchers):
        raise HeadlessTransitionError("Voucher slot is out of range")

    item = state.shop_vouchers[slot]
    if not isinstance(item, GeneratedShopVoucherItem):
        raise HeadlessTransitionError("Ante Voucher requires exact generated Voucher metadata")
    key = item.center_key
    if key not in EXACT_ANTE_VOUCHER_KEYS:
        raise HeadlessTransitionError("Voucher is not an exact Ante Voucher")
    if key in state.vouchers:
        raise HeadlessTransitionError("Voucher is already owned")
    if key == "v_petroglyph" and "v_hieroglyph" not in state.vouchers:
        raise HeadlessTransitionError("Petroglyph requires Hieroglyph ownership")

    if type(item.price) is not int or item.price < 0:
        raise HeadlessTransitionError("Voucher price must be an exact nonnegative integer")
    if state.money < item.price:
        raise HeadlessTransitionError("shop item is not affordable")
    if isinstance(state.ante, bool) or not isinstance(state.ante, int):
        raise HeadlessTransitionError("Ante must be an exact integer")

    # At an active normal shop after reset_blinds, vanilla blind_ante tracks the
    # same current Ante. A disagreement means the private progression snapshot is
    # stale; never repair it from the public value.
    if progression.blind_ante != state.ante:
        raise HeadlessTransitionError(
            "private blind Ante is stale relative to public Ante"
        )

    if key == "v_hieroglyph":
        if state.round_reset_hands_observed is not True:
            raise HeadlessTransitionError("next-round hand allowance is unobserved")
        if type(state.round_reset_hands) is not int or state.round_reset_hands < 1:
            raise HeadlessTransitionError(
                "Hieroglyph requires a reducible exact next-round hand allowance"
            )
        if type(state.hands_remaining) is not int or state.hands_remaining < 1:
            raise HeadlessTransitionError(
                "Hieroglyph requires a reducible exact current hand allowance"
            )
    else:
        if state.round_reset_discards_observed is not True:
            raise HeadlessTransitionError("next-round discard allowance is unobserved")
        if type(state.round_reset_discards) is not int or state.round_reset_discards < 1:
            raise HeadlessTransitionError(
                "Petroglyph requires a reducible exact next-round discard allowance"
            )
        if type(state.discards_remaining) is not int or state.discards_remaining < 1:
            raise HeadlessTransitionError(
                "Petroglyph requires a reducible exact current discard allowance"
            )

    return item, key, progression


def ante_voucher_redemption_is_exact(
    run: HeadlessRunState,
    *,
    slot: int,
) -> bool:
    """Return whether retained-state Hieroglyph/Petroglyph redemption is exact."""
    try:
        _validate_exact_redeem_boundary(run, slot=slot)
    except (TypeError, HeadlessTransitionError):
        return False
    return True


def redeem_exact_ante_voucher(
    run: HeadlessRunState,
    *,
    slot: int,
) -> HeadlessRunState:
    """Apply pinned vanilla Hieroglyph/Petroglyph direct state effects exactly.

    The successor run atomically contains both public mutations and the matching
    private ``blind_ante`` mutation. No RNG is consumed; the input is untouched.
    """
    item, key, _ = _validate_exact_redeem_boundary(run, slot=slot)

    next_run = run.copy()
    next_progression = next_run.require_blind_progression_state()
    state = next_run.public

    state.money -= item.price
    state.shop_vouchers.pop(slot)
    state.vouchers.append(key)
    state.vouchers_observed = True

    state.ante -= 1
    next_progression.blind_ante -= 1

    if key == "v_hieroglyph":
        state.round_reset_hands -= 1
        state.hands_remaining -= 1
    else:
        state.round_reset_discards -= 1
        state.discards_remaining -= 1

    return next_run
