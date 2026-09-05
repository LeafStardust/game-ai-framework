"""Pinned vanilla Tarot/Planet center order for exact shop identity RNG.

Balatro's ``get_current_pool`` preserves every center position and replaces
ineligible centers with the literal string ``UNAVAILABLE``.  Identity selection
therefore depends on the source pool order even when only a subset is currently
eligible.  These tuples pin the normal 1.0.1f center order from the project's
vanilla source commit.
"""

from __future__ import annotations

from collections.abc import Collection


VANILLA_TAROT_CENTER_ORDER: tuple[str, ...] = (
    "c_fool",
    "c_magician",
    "c_high_priestess",
    "c_empress",
    "c_emperor",
    "c_heirophant",
    "c_lovers",
    "c_chariot",
    "c_justice",
    "c_hermit",
    "c_wheel_of_fortune",
    "c_strength",
    "c_hanged_man",
    "c_death",
    "c_temperance",
    "c_devil",
    "c_tower",
    "c_star",
    "c_moon",
    "c_sun",
    "c_judgement",
    "c_world",
)

VANILLA_PLANET_CENTER_ORDER: tuple[str, ...] = (
    "c_mercury",
    "c_venus",
    "c_earth",
    "c_mars",
    "c_jupiter",
    "c_saturn",
    "c_uranus",
    "c_neptune",
    "c_pluto",
    "c_planet_x",
    "c_ceres",
    "c_eris",
)


_CENTER_ORDER_BY_TYPE = {
    "Tarot": VANILLA_TAROT_CENTER_ORDER,
    "Planet": VANILLA_PLANET_CENTER_ORDER,
}

_FALLBACK_BY_TYPE = {
    "Tarot": "c_strength",
    "Planet": "c_pluto",
}


def vanilla_consumable_center_order(card_type: str) -> tuple[str, ...]:
    try:
        return _CENTER_ORDER_BY_TYPE[card_type]
    except KeyError as exc:
        raise ValueError("card_type must be Tarot or Planet") from exc


def current_consumable_pool_from_eligible_keys(
    card_type: str,
    eligible_keys: Collection[str],
) -> tuple[str, ...]:
    """Rebuild vanilla's position-preserving current pool exactly.

    The caller must supply authoritative eligibility. Unknown keys are rejected
    instead of being ignored. If every source position is unavailable, vanilla
    replaces the whole pool with its type-specific one-card fallback.
    """
    order = vanilla_consumable_center_order(card_type)
    if isinstance(eligible_keys, (str, bytes)) or not isinstance(eligible_keys, Collection):
        raise TypeError("eligible_keys must be a collection of center keys")
    eligible = set(eligible_keys)
    if any(not isinstance(key, str) or not key for key in eligible):
        raise ValueError("eligible consumable center keys must be nonempty strings")
    unknown = eligible.difference(order)
    if unknown:
        raise ValueError(
            "eligible consumable pool contains unknown vanilla center keys: "
            + ", ".join(sorted(unknown))
        )

    if not eligible:
        return (_FALLBACK_BY_TYPE[card_type],)
    return tuple(key if key in eligible else "UNAVAILABLE" for key in order)
