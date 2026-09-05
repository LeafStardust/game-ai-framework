"""Explicit Voucher capability boundaries for exact headless mechanics.

Voucher *ownership* is not equivalent to owning every downstream consequence.
Each boundary below admits only the Voucher families whose effects are explicitly
owned there. Unsupported modifiers remain fail closed rather than inheriting a
single global "supported Voucher" flag.
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

EXACT_EDITION_RATE_VOUCHER_KEYS = frozenset(
    {
        "v_hone",
        "v_glow_up",
    }
)

# Resource Vouchers are neutral to ordinary main-shop generation. Hone/Glow Up
# are neutral to type/rarity/center/pricing generation but intentionally modify
# the ordinary Joker edition poll. The edition-rate relationship is therefore
# validated separately below before any shop RNG may be consumed.
SHOP_BASE_GENERATION_VOUCHER_KEYS = (
    EXACT_RESOURCE_VOUCHER_KEYS | EXACT_EDITION_RATE_VOUCHER_KEYS
)


def expected_joker_edition_rate_for_vouchers(
    state: BalatroState,
) -> float | None:
    """Return the exact vanilla edition rate implied by supported ownership.

    Vanilla redemption assigns ``G.GAME.edition_rate`` directly: Hone -> 2 and
    Glow Up -> 4. Glow Up requires Hone, so a used-Voucher state containing Glow
    Up without Hone is not a legal vanilla progression and fails closed.
    ``None`` means the current Voucher set is unsupported or structurally invalid.
    """
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")

    vouchers = state.vouchers
    if not isinstance(vouchers, list):
        return None
    if any(not isinstance(key, str) or not key for key in vouchers):
        return None
    if len(vouchers) != len(set(vouchers)):
        return None
    if vouchers and state.vouchers_observed is not True:
        return None
    if any(key not in SHOP_BASE_GENERATION_VOUCHER_KEYS for key in vouchers):
        return None

    owned = set(vouchers)
    if "v_glow_up" in owned and "v_hone" not in owned:
        return None
    if "v_glow_up" in owned:
        return 4.0
    if "v_hone" in owned:
        return 2.0
    return 1.0


def shop_generation_vouchers_are_exact(state: BalatroState) -> bool:
    """Return whether owned Vouchers and edition-rate state are base-shop exact."""
    expected_rate = expected_joker_edition_rate_for_vouchers(state)
    if expected_rate is None:
        return False

    rate = state.joker_generation_edition_rate
    if isinstance(rate, bool) or not isinstance(rate, (int, float)):
        return False
    return float(rate) == expected_rate
