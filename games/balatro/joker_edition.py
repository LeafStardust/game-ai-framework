from __future__ import annotations


def joker_has_negative_edition(item: object | None) -> bool:
    """Return whether a modeled Joker has Balatro's slot-neutral Negative edition."""
    if item is None:
        return False

    edition = getattr(item, "edition", None)
    if isinstance(edition, dict):
        return any(
            bool(enabled) and str(name).upper() == "NEGATIVE"
            for name, enabled in edition.items()
        )

    return str(edition or "").upper() == "NEGATIVE"
