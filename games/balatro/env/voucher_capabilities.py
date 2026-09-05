"""Explicit Voucher capability boundaries for exact headless mechanics.

Voucher *ownership* is not equivalent to owning every downstream consequence.
This module names only the centers whose currently implemented redemption effects
are neutral to ordinary main-shop type/identity/edition/pricing generation.
Unsupported Voucher modifiers must remain fail closed at the boundary they alter.
"""

from __future__ import annotations

from games.balatro.state import BalatroState


EXACT_RESOURCE_VOUCHER_KEYS = frozenset(
    {
        "v_crystal_ball",
        "v_grabber",
        "v_nacho_tong",
        "v_wasteful",
        "v_recyclomancy",
        "v_antimatter",
        "v_paint_brush",
        "v_palette",
    }
)

# None of the first exact redemption group changes ordinary main-shop card type
# rates, edition rate, inflation, discount percent, or the vanilla two-card main
# shop area capacity.  This alias is intentionally separate so future exact
# Voucher families need an explicit audit before joining this boundary.
SHOP_GENERATION_NEUTRAL_VOUCHER_KEYS = EXACT_RESOURCE_VOUCHER_KEYS


def shop_generation_vouchers_are_exact(state: BalatroState) -> bool:
    """Return whether current owned Vouchers are safe for base shop generation."""
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")
    vouchers = state.vouchers
    if not isinstance(vouchers, list):
        return False
    if any(not isinstance(key, str) or not key for key in vouchers):
        return False
    if len(vouchers) != len(set(vouchers)):
        return False
    # Nonempty ownership must come from an authoritative source.  Preserve the
    # legacy pristine-empty headless boundary while reset ownership is migrated
    # to an explicit observed-empty state.
    if vouchers and state.vouchers_observed is not True:
        return False
    return all(key in SHOP_GENERATION_NEUTRAL_VOUCHER_KEYS for key in vouchers)
