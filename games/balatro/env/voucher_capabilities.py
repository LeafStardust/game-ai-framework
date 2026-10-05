"""Explicit Voucher capability boundaries for exact headless mechanics.

Voucher *ownership* is not equivalent to owning every downstream consequence.
Each boundary below admits only the Voucher families whose effects are explicitly
owned there. Unsupported modifiers remain fail closed rather than inheriting a
single global "supported Voucher" flag.
"""

from __future__ import annotations

from games.balatro.state import BalatroState


EXACT_HAND_SIZE_VOUCHER_KEYS = frozenset({"v_paint_brush", "v_palette"})
EXACT_ROUND_RESOURCE_VOUCHER_KEYS = frozenset(
    {"v_grabber", "v_nacho_tong", "v_wasteful", "v_recyclomancy"}
)
EXACT_RESOURCE_VOUCHER_KEYS = frozenset(
    {
        "v_crystal_ball", "v_antimatter",
    }
) | EXACT_HAND_SIZE_VOUCHER_KEYS | EXACT_ROUND_RESOURCE_VOUCHER_KEYS
EXACT_EDITION_RATE_VOUCHER_KEYS = frozenset({"v_hone", "v_glow_up"})
EXACT_DISCOUNT_VOUCHER_KEYS = frozenset({"v_clearance_sale", "v_liquidation"})
EXACT_SHOP_TYPE_RATE_VOUCHER_KEYS = frozenset(
    {"v_tarot_merchant", "v_tarot_tycoon", "v_planet_merchant", "v_planet_tycoon"}
)
EXACT_REROLL_COST_VOUCHER_KEYS = frozenset({"v_reroll_surplus", "v_reroll_glut"})
EXACT_INTEREST_CAP_VOUCHER_KEYS = frozenset({"v_seed_money", "v_money_tree"})
EXACT_SHOP_SIZE_VOUCHER_KEYS = frozenset({"v_overstock_norm", "v_overstock_plus"})
EXACT_ANTE_VOUCHER_KEYS = frozenset({"v_hieroglyph", "v_petroglyph"})

# Crystal Ball's capacity change, Grabber/Wasteful round-resource changes,
# Hone's Joker-edition generation rate, the Overstock family's main-shop
# capacity changes, and the reroll-cost family's reset-cost changes are persisted
# when redeemed; none has a callback during Boss cash-out. Their histories are
# consumed later by the exact resource/shop owners.
# Keep this boundary deliberately narrower than general Voucher support:
# payout/interest/pricing modifiers require their own exact Boss cash-out
# ownership before they may cross that transition.
EXACT_BOSS_CASH_OUT_NO_EFFECT_VOUCHER_KEYS = frozenset(
    {"v_crystal_ball", "v_hone"}
) | (
    EXACT_SHOP_SIZE_VOUCHER_KEYS
    | EXACT_SHOP_TYPE_RATE_VOUCHER_KEYS
    | EXACT_REROLL_COST_VOUCHER_KEYS
    | EXACT_HAND_SIZE_VOUCHER_KEYS
    | EXACT_ROUND_RESOURCE_VOUCHER_KEYS
    | EXACT_ANTE_VOUCHER_KEYS
)

# These Vouchers have no effect on ordinary base-shop generation. They are
# nevertheless admitted explicitly at this boundary so authoritative ownership
# does not become "inexact" merely because another exact subsystem owns their
# consequences. Omen Globe only modifies Arcana-pack Spectral generation;
# Telescope only changes Celestial-pack Planet selection.
EXACT_SHOP_BASE_NO_EFFECT_VOUCHER_KEYS = frozenset(
    {"v_omen_globe", "v_telescope"}
)

SHOP_BASE_GENERATION_VOUCHER_KEYS = (
    EXACT_RESOURCE_VOUCHER_KEYS
    | EXACT_EDITION_RATE_VOUCHER_KEYS
    | EXACT_DISCOUNT_VOUCHER_KEYS
    | EXACT_SHOP_TYPE_RATE_VOUCHER_KEYS
    | EXACT_REROLL_COST_VOUCHER_KEYS
    | EXACT_INTEREST_CAP_VOUCHER_KEYS
    | EXACT_SHOP_SIZE_VOUCHER_KEYS
    | EXACT_ANTE_VOUCHER_KEYS
    | EXACT_SHOP_BASE_NO_EFFECT_VOUCHER_KEYS
)

# Reroll cost is a narrower capability than base-shop generation. Every Voucher
# admitted here has either an explicitly owned reroll-cost effect or an audited
# zero effect on ordinary paid rerolls. Keep this boundary independent so adding
# or withholding support for another shop-generation consequence cannot silently
# change whether reroll cost itself is exact.
REROLL_COST_EXACT_VOUCHER_KEYS = (
    SHOP_BASE_GENERATION_VOUCHER_KEYS
)


def _owned_supported_vouchers(
    state: BalatroState,
    supported_keys: frozenset[str] = SHOP_BASE_GENERATION_VOUCHER_KEYS,
) -> set[str] | None:
    vouchers = state.vouchers
    if not isinstance(vouchers, list):
        return None
    if any(not isinstance(key, str) or not key for key in vouchers):
        return None
    if len(vouchers) != len(set(vouchers)):
        return None
    if vouchers and state.vouchers_observed is not True:
        return None
    if any(key not in supported_keys for key in vouchers):
        return None
    owned = set(vouchers)
    if "v_petroglyph" in owned and "v_hieroglyph" not in owned:
        return None
    return owned


def blind_start_vouchers_are_exact(state: BalatroState) -> bool:
    """Return whether Voucher ownership may cross blind start unchanged.

    Supported Voucher consequences are either persisted into canonical state at
    redemption (resource/capacity and Ante effects) or consumed by downstream
    shop/economy owners. Vanilla blind selection does not reapply these Voucher
    effects during the ``setting_blind`` lifecycle. Therefore blind start only
    needs complete, authoritative, supported ownership; it must not replay the
    Voucher effects a second time.
    """
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")
    return _owned_supported_vouchers(state) is not None


def boss_cash_out_vouchers_are_exact(
    state: BalatroState,
    *,
    base_reroll_cost: object,
    reroll_cost: object,
    boss_hand_size_sub: object,
    blind_ante: object,
) -> bool:
    """Return whether owned Vouchers are exact at Boss cash-out/shop entry."""
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")
    owned = _owned_supported_vouchers(
        state,
        EXACT_BOSS_CASH_OUT_NO_EFFECT_VOUCHER_KEYS,
    )
    if owned is None:
        return False
    if "v_overstock_plus" in owned and "v_overstock_norm" not in owned:
        return False

    expected_consumable_slots = 3 if "v_crystal_ball" in owned else 2
    expected_edition_rate = 2.0 if "v_hone" in owned else 1.0
    expected_tarot_rate = expected_tarot_rate_for_vouchers(state)
    expected_planet_rate = expected_planet_rate_for_vouchers(state)
    expected_reroll_cost = expected_base_reroll_cost_for_vouchers(state)
    expected_hand_size = expected_red_deck_hand_size_for_vouchers(state)
    expected_round_resources = expected_red_deck_round_resources_for_vouchers(state)
    if (
        expected_tarot_rate is None
        or expected_planet_rate is None
        or expected_reroll_cost is None
        or expected_hand_size is None
        or expected_round_resources is None
    ):
        return False
    if owned & EXACT_HAND_SIZE_VOUCHER_KEYS:
        # Cash-out support for this newly admitted family is deliberately narrow:
        # Joker hand-size composition remains a separate callback capability.
        if state.jokers:
            return False
        if state.boss_name == "The Manacle":
            if (
                type(boss_hand_size_sub) is not int
                or boss_hand_size_sub != 1
                or state.hand_size != expected_hand_size - 1
            ):
                return False
        elif boss_hand_size_sub is not None or state.hand_size != expected_hand_size:
            return False
    if owned & (EXACT_ANTE_VOUCHER_KEYS | EXACT_ROUND_RESOURCE_VOUCHER_KEYS):
        if state.jokers:
            return False
        expected_hands, expected_discards = expected_round_resources
        if (
            state.round_reset_hands_observed is not True
            or state.round_reset_discards_observed is not True
            or type(state.round_reset_hands) is not int
            or state.round_reset_hands != expected_hands
            or type(state.round_reset_discards) is not int
            or state.round_reset_discards != expected_discards
        ):
            return False
        if owned & EXACT_ANTE_VOUCHER_KEYS and (
            type(state.ante) is not int
            or type(blind_ante) is not int
            or state.ante != blind_ante + 1
        ):
            return False
    slots = state.consumable_slots
    edition = state.joker_generation_edition_rate
    tarot = state.tarot_rate
    planet = state.planet_rate
    return (
        type(slots) is int
        and slots == expected_consumable_slots
        and not isinstance(edition, bool)
        and isinstance(edition, (int, float))
        and float(edition) == expected_edition_rate
        and not isinstance(tarot, bool)
        and isinstance(tarot, (int, float))
        and float(tarot) == expected_tarot_rate
        and not isinstance(planet, bool)
        and isinstance(planet, (int, float))
        and float(planet) == expected_planet_rate
        and type(base_reroll_cost) is int
        and base_reroll_cost == expected_reroll_cost
        and type(reroll_cost) is int
        and reroll_cost >= base_reroll_cost
    )


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
    owned = _owned_supported_vouchers(state, REROLL_COST_EXACT_VOUCHER_KEYS)
    if owned is None or ("v_reroll_glut" in owned and "v_reroll_surplus" not in owned):
        return None
    if "v_reroll_glut" in owned:
        return 1
    if "v_reroll_surplus" in owned:
        return 3
    return 5


def expected_red_deck_hand_size_for_vouchers(state: BalatroState) -> int | None:
    """Return exact persistent Red Deck hand size from Voucher history."""
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")
    owned = _owned_supported_vouchers(state)
    if owned is None or ("v_palette" in owned and "v_paint_brush" not in owned):
        return None
    return 8 + int("v_paint_brush" in owned) + int("v_palette" in owned)


def expected_red_deck_round_resources_for_vouchers(
    state: BalatroState,
) -> tuple[int, int] | None:
    """Return exact persistent Red Deck reset hands/discards from Vouchers."""
    if not isinstance(state, BalatroState):
        raise TypeError("state must be BalatroState")
    owned = _owned_supported_vouchers(state)
    if owned is None:
        return None
    if "v_nacho_tong" in owned and "v_grabber" not in owned:
        return None
    if "v_recyclomancy" in owned and "v_wasteful" not in owned:
        return None
    hands = 4 + int("v_grabber" in owned) + int("v_nacho_tong" in owned)
    discards = 3 + int("v_wasteful" in owned) + int("v_recyclomancy" in owned)
    hands -= int("v_hieroglyph" in owned)
    discards -= int("v_petroglyph" in owned)
    return hands, discards


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
