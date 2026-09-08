"""Exact Red Deck / White Stake base blind amount through Ante 8.

Vanilla ``get_blind_amount(ante)`` deliberately returns 100 for every Ante below
1.  That behavior matters once Hieroglyph/Petroglyph can move
``round_resets.ante`` to zero or negative values.  The normal-mode Red/White
objective ends at Ante 8, so this owner intentionally stops there instead of
copying the endless-mode scaling formula before that boundary is needed.

This is the *base* amount only.  Small/Big/Boss center multipliers are separate
mechanics and must be applied by their exact owner before a ``Blind`` is started.
"""

from __future__ import annotations


class BlindRequirementError(ValueError):
    """Raised when the exact Red/White base blind amount is unavailable."""


_ANTE_ONE_TO_EIGHT_BASE: tuple[int, ...] = (
    300,
    800,
    2_000,
    5_000,
    11_000,
    20_000,
    35_000,
    50_000,
)


def red_white_base_blind_amount(ante: int) -> int:
    """Return vanilla ``get_blind_amount`` for Red/White through Ante 8.

    White Stake uses the normal 1.0 Ante scaling.  ``ante < 1`` is a real
    vanilla domain, not invalid input: it returns 100 and is reachable through
    Hieroglyph/Petroglyph.  Endless Ante > 8 remains fail-closed until its exact
    nonlinear formula is needed by the project objective.
    """
    if isinstance(ante, bool) or not isinstance(ante, int):
        raise BlindRequirementError("ante must be an exact integer")
    if ante < 1:
        return 100
    if ante <= 8:
        return _ANTE_ONE_TO_EIGHT_BASE[ante - 1]
    raise BlindRequirementError(
        "Red/White base blind amount beyond Ante 8 is not yet owned"
    )
