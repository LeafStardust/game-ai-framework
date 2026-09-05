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

EXACT_DISCOUNT_VOUCHER_KEYS = frozenset(
    {
        "v_clearance_sale",
        "v_liquidation",
    }
)

EXACT_SHOP_TYPE_RATE_VOUCHER_KEYS = frozenset(
    {
        "v_tarot_merchant",
        "v_tarot_tycoon",
        "v_planet_merchant",
        "v_planet_tycoon",
    }
)

# Resource Vouchers are neutral to ordinary main-shop generation. Hone/Glow Up
# modify the ordinary Joker edition poll. Clearance Sale/Liquidation modify card
# pricing but not shop RNG. Merchant/Tycoon Vouchers modify the Tarot/Planet
# weights consumed by the ordinary ``create_card_for_shop`` type poll itself.
SHOP_BASE_GENERATION_VOUCHER_KEYS = (
    EXACT_RESOURCE_VOUCHER_KEYS
    | EXACT_EDITION_RATE_VOUCHER_KEYS
    | EXACT_DISCOUNT_VOUCHER_KEYS
    | EXACT_SHOP_TYPE_RATE_VOUCHER_KEYS
)


def _owned_supported_vouchers(state: BalatroState) -> set[str] | None:
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
    return set(vouchers)


def expected_joker_edition_rate_for_vouchers(
    state: BalatroState,
) -> float | None:
    """Return the exact vanilla edition rate implied by supported ownership."""
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")

    owned = _owned_supported_vouchers(state)
    if owned is None:
        return None
    if "v_glow_up" in owned and "v_hone" not in owned:
        return None
    if "v_glow_up" in owned:
        return 4.0
    if "v_hone" in owned:
        return 2.0
    return 1.0


def expected_shop_discount_percent_for_vouchers(
    state: BalatroState,
) -> int | None:
    """Return vanilla ``G.GAME.discount_percent`` implied by exact ownership."""
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")

    owned = _owned_supported_vouchers(state)
    if owned is None:
        return None
    if "v_liquidation" in owned and "v_clearance_sale" not in owned:
        return None
    if "v_liquidation" in owned:
        return 50
    if "v_clearance_sale" in owned:
        return 25
    return 0


def expected_tarot_rate_for_vouchers(state: BalatroState) -> float | None:
    """Return vanilla ``G.GAME.tarot_rate`` implied by exact ownership.

    Pinned vanilla assigns ``4 * center.config.extra`` on redemption. Tarot
    Merchant uses ``9.6/4`` and Tarot Tycoon uses ``32/4``, producing exact
    conceptual rates 9.6 and 32. Tycoon without Merchant is impossible and fails
    closed rather than trusting a numeric rate alone.
    """
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")

    owned = _owned_supported_vouchers(state)
    if owned is None:
        return None
    if "v_tarot_tycoon" in owned and "v_tarot_merchant" not in owned:
        return None
    if "v_tarot_tycoon" in owned:
        return 32.0
    if "v_tarot_merchant" in owned:
        return 9.6
    return 4.0


def expected_planet_rate_for_vouchers(state: BalatroState) -> float | None:
    """Return vanilla ``G.GAME.planet_rate`` implied by exact ownership."""
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")

    owned = _owned_supported_vouchers(state)
    if owned is None:
        return None
    if "v_planet_tycoon" in owned and "v_planet_merchant" not in owned:
        return None
    if "v_planet_tycoon" in owned:
        return 32.0
    if "v_planet_merchant" in owned:
        return 9.6
    return 4.0


def shop_generation_vouchers_are_exact(state: BalatroState) -> bool:
    """Return whether Voucher effects consumed by shop RNG are exact."""
    expected_edition = expected_joker_edition_rate_for_vouchers(state)
    expected_discount = expected_shop_discount_percent_for_vouchers(state)
    expected_tarot = expected_tarot_rate_for_vouchers(state)
    expected_planet = expected_planet_rate_for_vouchers(state)
    if any(
        value is None
        for value in (
            expected_edition,
            expected_discount,
            expected_tarot,
            expected_planet,
        )
    ):
        return False

    edition = state.joker_generation_edition_rate
    tarot = state.tarot_rate
    planet = state.planet_rate
    for value in (edition, tarot, planet):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        if float(value) < 0.0:
            return False

    return (
        float(edition) == expected_edition
        and float(tarot) == expected_tarot
        and float(planet) == expected_planet
    )


def shop_pricing_vouchers_are_exact(state: BalatroState) -> bool:
    """Return whether Voucher-derived shop pricing state is authoritative/exact."""
    if not shop_generation_vouchers_are_exact(state):
        return False
    expected_discount = expected_shop_discount_percent_for_vouchers(state)
    if expected_discount is None:
        return False
    if state.shop_discount_percent_observed is not True:
        return False
    discount = state.shop_discount_percent
    return type(discount) is int and discount == expected_discount
