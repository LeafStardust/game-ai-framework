from __future__ import annotations

"""Shared mechanical authority for Jokers that scale whenever a Planet is used."""


_PLANET_USE_SCALERS = frozenset({"ConstellationJoker"})


def has_planet_use_scaler(state) -> bool:
    """Return whether public owned-Joker state contains an active Planet-use scaler.

    This helper intentionally encodes the game mechanic in one place. Downstream
    acquisition/timing policies consume the capability instead of independently
    hardcoding Constellation-specific strategic exceptions.
    """
    return any(
        type(joker).__name__ in _PLANET_USE_SCALERS
        and not bool(getattr(joker, "debuffed", False))
        for joker in tuple(getattr(state, "jokers", ()) or ())
    )
