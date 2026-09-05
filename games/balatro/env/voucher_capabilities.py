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
        "v_crystal_ball", "v_grabber", "v_nacho_tong", "v_wasteful",
        "v_recyclomancy", "v_antimatter", "v_paint_brush", "v_palette",
    }
)
EXACT_EDITION_RATE_VOUCHER_KEYS = frozenset({"v_hone", "v_glow_up"})
EXACT_DISCOUNT_VOUCHER_KEYS = frozenset({"v_clearance_sale", "v_liquidation"})
EXACT_SHOP_TYPE_RATE_VOUCHER_KEYS = frozenset(
    {"v_tarot_merchant", "v_tarot_tycoon", "v_planet_merchant", "v_planet_tycoon"}
)
EXACT_REROLL_COST_VOUCHER_KEYS = frozenset({"v_reroll_surplus", "v_reroll_glut"})
EXACT_INTEREST_CAP_VOUCHER_KEYS = frozenset({"v_seed_money", "v_money_tree"})
EXACT_SHOP_SIZE_VOUCHER_KEYS = frozenset({"v_overstock_norm", "v_overstock_plus"})

SHOP_BASE_GENERATION_VOUCHER_KEYS = (
    EXACT_RESOURCE_VOUCHER_KEYS
    | EXACT_EDITION_RATE_VOUCHER_KEYS
    | EXACT_DISCOUNT_VOUCHER_KEYS
    | EXACT_SHOP_TYPE_RATE_VOUCHER_KEYS
    | EXACT_REROLL_COST_VOUCHER_KEYS
    | EXACT_INTEREST_CAP_VOUCHER_KEYS
    | EXACT_SHOP_SIZE_VOUCHER_KEYS
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


def expected_joker_edition_rate_for_vouchers(state: BalatroState) -> float | None:
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")
    owned = _owned_supported_vouchers(state)
    if owned is None or ("v_glow_up" in owned and "v_hone" not in owned):
        return None
    if "v_glow_up" in owned:
        return 4.0
    if "v_hone" in owned:
        return 2.0
    return 1.0


def expected_shop_discount_percent_for_vouchers(state: BalatroState) -> int | None:
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")
    owned = _owned_supported_vouchers(state)
    if owned is None or ("v_liquidation" in owned and "v_clearance_sale" not in owned):
        return None
    if "v_liquidation" in owned:
        return 50
    if "v_clearance_sale" in owned:
        return 25
    return 0


def expected_tarot_rate_for_vouchers(state: BalatroState) -> float | None:
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")
    owned = _owned_supported_vouchers(state)
    if owned is None or ("v_tarot_tycoon" in owned and "v_tarot_merchant" not in owned):
        return None
    if "v_tarot_tycoon" in owned:
        return 32.0
    if "v_tarot_merchant" in owned:
        return 9.6
    return 4.0


def expected_planet_rate_for_vouchers(state: BalatroState) -> float | None:
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")
    owned = _owned_supported_vouchers(state)
    if owned is None or ("v_planet_tycoon" in owned and "v_planet_merchant" not in owned):
        return None
    if "v_planet_tycoon" in owned:
        return 32.0
    if "v_planet_merchant" in owned:
        return 9.6
    return 4.0


def expected_base_reroll_cost_for_vouchers(state: BalatroState) -> int | None:
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")
    owned = _owned_supported_vouchers(state)
    if owned is None or ("v_reroll_glut" in owned and "v_reroll_surplus" not in owned):
        return None
    if "v_reroll_glut" in owned:
        return 1
    if "v_reroll_surplus" in owned:
        return 3
    return 5


def expected_interest_cap_for_vouchers(state: BalatroState) -> int | None:
    """Return exact vanilla normal-mode interest cap from Voucher history.

    Pinned source has exactly two normal-mode writers of G.GAME.interest_cap:
    initialization to $25 and redemption of Seed Money/Money Tree to their
    center extras ($50/$100). Therefore a complete authoritative used_vouchers
    table is sufficient to reconstruct the cap without exposing a redundant
    live memory field.
    """
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")
    owned = _owned_supported_vouchers(state)
    if owned is None or ("v_money_tree" in owned and "v_seed_money" not in owned):
        return None
    if "v_money_tree" in owned:
        return 100
    if "v_seed_money" in owned:
        return 50
    return 25


def expected_main_shop_slots_for_vouchers(state: BalatroState) -> int | None:
    """Return exact Red-Deck main-shop capacity from Voucher history.

    Normal Red Deck starts each shop with ``joker_max = 2``. Pinned vanilla has
    Overstock and Overstock Plus each call ``change_shop_size(1)`` when redeemed.
    Their order is a strict progression, so authoritative used-Voucher history is
    sufficient to reconstruct capacity as 2 / 3 / 4 without exposing UI geometry
    or a duplicate simulator-only public field.
    """
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")
    owned = _owned_supported_vouchers(state)
    if owned is None or (
        "v_overstock_plus" in owned and "v_overstock_norm" not in owned
    ):
        return None
    if "v_overstock_plus" in owned:
        return 4
    if "v_overstock_norm" in owned:
        return 3
    return 2


def interest_cap_vouchers_are_exact(state: BalatroState) -> bool:
    expected = expected_interest_cap_for_vouchers(state)
    if expected is None:
        return False
    # Headless redemption persists the explicit numeric field. If another source
    # explicitly claims it observed a cap, require consistency; otherwise the
    # authoritative Voucher history above is already an exact reconstruction.
    if state.interest_cap_observed is True:
        return type(state.interest_cap) is int and state.interest_cap == expected
    return True


def shop_generation_vouchers_are_exact(state: BalatroState) -> bool:
    expected_edition = expected_joker_edition_rate_for_vouchers(state)
    expected_discount = expected_shop_discount_percent_for_vouchers(state)
    expected_tarot = expected_tarot_rate_for_vouchers(state)
    expected_planet = expected_planet_rate_for_vouchers(state)
    expected_reroll = expected_base_reroll_cost_for_vouchers(state)
    expected_slots = expected_main_shop_slots_for_vouchers(state)
    if any(
        value is None
        for value in (
            expected_edition,
            expected_discount,
            expected_tarot,
            expected_planet,
            expected_reroll,
            expected_slots,
        )
    ):
        return False
    edition = state.joker_generation_edition_rate
    tarot = state.tarot_rate
    planet = state.planet_rate
    for value in (edition, tarot, planet):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or float(value) < 0.0:
            return False
    return (
        float(edition) == expected_edition
        and float(tarot) == expected_tarot
        and float(planet) == expected_planet
    )


def shop_pricing_vouchers_are_exact(state: BalatroState) -> bool:
    if not shop_generation_vouchers_are_exact(state):
        return False
    expected_discount = expected_shop_discount_percent_for_vouchers(state)
    if expected_discount is None or state.shop_discount_percent_observed is not True:
        return False
    discount = state.shop_discount_percent
    return type(discount) is int and discount == expected_discount
