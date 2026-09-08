from __future__ import annotations

from typing import Mapping


EDITION_UNIVERSAL_VALUES = {
    "FOIL": 0.8,
    "HOLO": 1.5,
    "HOLOGRAPHIC": 1.5,
    "POLYCHROME": 2.5,
    "NEGATIVE": 4.0,
}


def joker_edition_name(item: object | None) -> str | None:
    if item is None:
        return None
    edition = getattr(item, "edition", None)
    if isinstance(edition, Mapping):
        edition = next(
            (name for name, enabled in edition.items() if bool(enabled)),
            None,
        )
    if not edition:
        return None
    return str(edition).upper()


def joker_edition_universal_value(item: object | None) -> float:
    """Return strategy-independent acquisition/retention value for an edition."""

    return EDITION_UNIVERSAL_VALUES.get(joker_edition_name(item) or "", 0.0)


def joker_has_negative_edition(item: object | None) -> bool:
    """Return whether a modeled Joker has Balatro's slot-neutral Negative edition."""
    if item is None:
        return False

    return joker_edition_name(item) == "NEGATIVE"
