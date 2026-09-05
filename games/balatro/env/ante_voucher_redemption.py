"""Exact internal redemption primitive for Hieroglyph / Petroglyph.

This owner deliberately keeps ``BlindProgressionState`` explicit.  Vanilla
redemption mutates both policy-visible run state (Ante and round allowances) and
private ``G.GAME.round_resets.blind_ante``.  Until that private progression state
is installed in the generic training run container, this primitive must not be
mistaken for training-visible ``BUY_VOUCHER`` ownership.
"""

from __future__ import annotations

from copy import deepcopy

from games.balatro.env.blind_progression import BlindProgressionState
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


EXACT_ANTE_VOUCHER_KEYS = frozenset({"v_hieroglyph", "v_petroglyph"})


def _validate_exact_redeem_boundary(
    run: HeadlessRunState,
    progression: BlindProgressionState,
    *,
    slot: int,
) -> tuple[GeneratedShopVoucherItem, str]:
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if not isinstance(progression, BlindProgressionState):
        raise TypeError("progression must be BlindProgressionState")
    if isinstance(slot, bool) or not isinstance(slot, int):
        raise HeadlessTransitionError("Voucher slot must be an exact integer")

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

    # At an active normal shop, source round_resets.blind_ante tracks the same
    # current Ante.  Boss cash-out reset_blinds and each Ante Voucher move both
    # fields together.  A disagreement means the private progression snapshot is
    # stale and redemption cannot be reproduced exactly.
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

    return item, key


def ante_voucher_redemption_is_exact(
    run: HeadlessRunState,
    progression: BlindProgressionState,
    *,
    slot: int,
) -> bool:
    """Return whether the internal Hieroglyph/Petroglyph redemption is exact."""
    try:
        _validate_exact_redeem_boundary(run, progression, slot=slot)
    except (TypeError, HeadlessTransitionError):
        return False
    return True


def redeem_exact_ante_voucher(
    run: HeadlessRunState,
    progression: BlindProgressionState,
    *,
    slot: int,
) -> tuple[HeadlessRunState, BlindProgressionState]:
    """Apply pinned vanilla Hieroglyph/Petroglyph direct state effects.

    Source order/effects represented here:

    * pay and consume the shop Voucher;
    * ``ease_ante(-1)`` -> persistent Ante decreases by one;
    * ``round_resets.blind_ante`` decreases by one;
    * Hieroglyph decreases both persistent and current hands by one;
    * Petroglyph (requiring Hieroglyph) decreases both persistent and current
      discards by one;
    * used-Voucher ownership is appended.

    No RNG is consumed.  Inputs are never mutated.
    """
    item, key = _validate_exact_redeem_boundary(run, progression, slot=slot)

    next_run = run.copy()
    next_progression = deepcopy(progression)
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

    return next_run, next_progression
