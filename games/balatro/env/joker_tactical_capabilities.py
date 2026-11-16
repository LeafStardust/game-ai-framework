"""Exact tactical callback capability for generated gameplay Jokers."""

from __future__ import annotations

from typing import Any

from games.balatro.jokers.droll_joker import DrollJoker
from games.balatro.jokers.even_steven import EvenStevenJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.odd_todd import OddToddJoker


def generated_joker_tactical_callbacks_are_exact(jokers: list[Any]) -> bool:
    """Return whether every owned Joker has only the currently owned callbacks."""
    for joker in jokers:
        if type(joker) is FlatMultJoker:
            if type(joker.mult) is not int or joker.mult != 4:
                return False
            expected_center = "j_joker"
        elif type(joker) is DrollJoker:
            expected_center = "j_droll"
        elif type(joker) is EvenStevenJoker:
            expected_center = "j_even_steven"
        elif type(joker) is OddToddJoker:
            expected_center = "j_odd_todd"
        else:
            return False
        if getattr(joker, "center", None) != expected_center:
            return False
        if getattr(joker, "edition", None) is not None:
            return False
        if getattr(joker, "debuffed", False) is not False:
            return False
    return True
