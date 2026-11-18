"""Exact tactical callback capability for generated gameplay Jokers."""

from __future__ import annotations

from typing import Any

from games.balatro.jokers.abstract_joker import AbstractJoker
from games.balatro.jokers.banner import BannerJoker
from games.balatro.jokers.blue_joker import BlueJoker
from games.balatro.jokers.clever_joker import CleverJoker
from games.balatro.jokers.devious_joker import DeviousJoker
from games.balatro.jokers.droll_joker import DrollJoker
from games.balatro.jokers.even_steven import EvenStevenJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.gluttonous_joker import GluttonousJoker
from games.balatro.jokers.half_joker import HalfJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.mad_joker import MadJoker
from games.balatro.jokers.mystic_summit import MysticSummitJoker
from games.balatro.jokers.odd_todd import OddToddJoker
from games.balatro.jokers.photograph import PhotographJoker
from games.balatro.jokers.raised_fist import RaisedFistJoker
from games.balatro.jokers.scholar import ScholarJoker
from games.balatro.jokers.scary_face import ScaryFaceJoker
from games.balatro.jokers.sly_joker import SlyJoker
from games.balatro.jokers.smiley_face import SmileyFaceJoker
from games.balatro.jokers.walkie_talkie import WalkieTalkieJoker
from games.balatro.jokers.wily_joker import WilyJoker


def generated_joker_tactical_callbacks_are_exact(jokers: list[Any]) -> bool:
    """Return whether every owned Joker has only the currently owned callbacks."""
    for joker in jokers:
        if type(joker) is AbstractJoker:
            expected_center = "j_abstract"
        elif type(joker) is BannerJoker:
            expected_center = "j_banner"
        elif type(joker) is BlueJoker:
            expected_center = "j_blue_joker"
        elif type(joker) is CleverJoker:
            expected_center = "j_clever"
        elif type(joker) is FlatMultJoker:
            if type(joker.mult) is not int or joker.mult != 4:
                return False
            expected_center = "j_joker"
        elif type(joker) is DeviousJoker:
            expected_center = "j_devious"
        elif type(joker) is DrollJoker:
            expected_center = "j_droll"
        elif type(joker) is EvenStevenJoker:
            expected_center = "j_even_steven"
        elif type(joker) is GluttonousJoker:
            expected_center = "j_gluttenous_joker"
        elif type(joker) is HalfJoker:
            expected_center = "j_half"
        elif type(joker) is JollyJoker:
            expected_center = "j_jolly"
        elif type(joker) is MadJoker:
            expected_center = "j_mad"
        elif type(joker) is MysticSummitJoker:
            expected_center = "j_mystic_summit"
        elif type(joker) is OddToddJoker:
            expected_center = "j_odd_todd"
        elif type(joker) is PhotographJoker:
            expected_center = "j_photograph"
        elif type(joker) is RaisedFistJoker:
            expected_center = "j_raised_fist"
        elif type(joker) is ScholarJoker:
            expected_center = "j_scholar"
        elif type(joker) is ScaryFaceJoker:
            expected_center = "j_scary_face"
        elif type(joker) is SlyJoker:
            expected_center = "j_sly"
        elif type(joker) is SmileyFaceJoker:
            expected_center = "j_smiley"
        elif type(joker) is WalkieTalkieJoker:
            expected_center = "j_walkie_talkie"
        elif type(joker) is WilyJoker:
            expected_center = "j_wily"
        else:
            return False
        if getattr(joker, "center", None) != expected_center:
            return False
        if getattr(joker, "edition", None) is not None:
            return False
        if getattr(joker, "debuffed", False) is not False:
            return False
    return True
