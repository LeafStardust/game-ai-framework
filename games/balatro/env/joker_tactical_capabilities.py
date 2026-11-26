"""Exact tactical callback capability for generated gameplay Jokers."""

from __future__ import annotations

import math
from typing import Any

from games.balatro.jokers.abstract_joker import AbstractJoker
from games.balatro.jokers.banner import BannerJoker
from games.balatro.jokers.blue_joker import BlueJoker
from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.clever_joker import CleverJoker
from games.balatro.jokers.cloud_9 import Cloud9Joker
from games.balatro.jokers.crazy_joker import CrazyJoker
from games.balatro.jokers.crafty_joker import CraftyJoker
from games.balatro.jokers.devious_joker import DeviousJoker
from games.balatro.jokers.droll_joker import DrollJoker
from games.balatro.jokers.drunkard import DrunkardJoker
from games.balatro.jokers.even_steven import EvenStevenJoker
from games.balatro.jokers.fibonacci import FibonacciJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.gluttonous_joker import GluttonousJoker
from games.balatro.jokers.golden_joker import GoldenJoker
from games.balatro.jokers.greedy_joker import GreedyJoker
from games.balatro.jokers.half_joker import HalfJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.juggler import JugglerJoker
from games.balatro.jokers.lusty_joker import LustyJoker
from games.balatro.jokers.mad_joker import MadJoker
from games.balatro.jokers.mystic_summit import MysticSummitJoker
from games.balatro.jokers.odd_todd import OddToddJoker
from games.balatro.jokers.photograph import PhotographJoker
from games.balatro.jokers.raised_fist import RaisedFistJoker
from games.balatro.jokers.castle import CASTLE_SUITS, CastleJoker
from games.balatro.jokers.rocket import RocketJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.jokers.midas_mask import MidasMaskJoker
from games.balatro.jokers.dna import DNAJoker
from games.balatro.jokers.faceless_joker import FacelessJoker
from games.balatro.jokers.madness import MadnessJoker, madness_x_mult_is_exact
from games.balatro.jokers.seance import SeanceJoker
from games.balatro.jokers.scholar import ScholarJoker
from games.balatro.jokers.scary_face import ScaryFaceJoker
from games.balatro.jokers.sly_joker import SlyJoker
from games.balatro.jokers.smiley_face import SmileyFaceJoker
from games.balatro.jokers.splash import SplashJoker
from games.balatro.jokers.vampire import VampireJoker
from games.balatro.jokers.walkie_talkie import WalkieTalkieJoker
from games.balatro.jokers.wily_joker import WilyJoker
from games.balatro.jokers.wrathful_joker import WrathfulJoker
from games.balatro.jokers.zany_joker import ZanyJoker


def generated_joker_tactical_callbacks_are_exact(
    jokers: list[Any], *, castle_suit: str | None = None
) -> bool:
    """Return whether every owned Joker has only the currently owned callbacks."""
    dna_seen = False
    for joker in jokers:
        if type(joker) is AbstractJoker:
            expected_center = "j_abstract"
        elif type(joker) is BannerJoker:
            expected_center = "j_banner"
        elif type(joker) is BlueJoker:
            expected_center = "j_blue_joker"
        elif type(joker) is BullJoker:
            expected_center = "j_bull"
        elif type(joker) is CleverJoker:
            expected_center = "j_clever"
        elif type(joker) is Cloud9Joker:
            expected_center = "j_cloud_9"
        elif type(joker) is CrazyJoker:
            expected_center = "j_crazy"
        elif type(joker) is CraftyJoker:
            expected_center = "j_crafty"
        elif type(joker) is FlatMultJoker:
            if type(joker.mult) is not int or joker.mult != 4:
                return False
            expected_center = "j_joker"
        elif type(joker) is DeviousJoker:
            expected_center = "j_devious"
        elif type(joker) is DrollJoker:
            expected_center = "j_droll"
        elif type(joker) is DrunkardJoker:
            expected_center = "j_drunkard"
        elif type(joker) is EvenStevenJoker:
            expected_center = "j_even_steven"
        elif type(joker) is FacelessJoker:
            expected_center = "j_faceless"
        elif type(joker) is FibonacciJoker:
            expected_center = "j_fibonacci"
        elif type(joker) is GluttonousJoker:
            expected_center = "j_gluttenous_joker"
        elif type(joker) is GoldenJoker:
            expected_center = "j_golden"
        elif type(joker) is GreedyJoker:
            expected_center = "j_greedy_joker"
        elif type(joker) is HalfJoker:
            expected_center = "j_half"
        elif type(joker) is JollyJoker:
            expected_center = "j_jolly"
        elif type(joker) is JugglerJoker:
            expected_center = "j_juggler"
        elif type(joker) is LustyJoker:
            expected_center = "j_lusty_joker"
        elif type(joker) is MadJoker:
            expected_center = "j_mad"
        elif type(joker) is MysticSummitJoker:
            expected_center = "j_mystic_summit"
        elif type(joker) is MimeJoker:
            expected_center = "j_mime"
        elif type(joker) is MidasMaskJoker:
            expected_center = "j_midas_mask"
        elif type(joker) is DNAJoker:
            if dna_seen:
                return False
            dna_seen = True
            expected_center = "j_dna"
        elif type(joker) is MadnessJoker:
            if not madness_x_mult_is_exact(joker.x_mult):
                return False
            expected_center = "j_madness"
        elif type(joker) is OddToddJoker:
            expected_center = "j_odd_todd"
        elif type(joker) is PhotographJoker:
            expected_center = "j_photograph"
        elif type(joker) is RaisedFistJoker:
            expected_center = "j_raised_fist"
        elif type(joker) is RocketJoker:
            if type(joker.dollars) is not int or joker.dollars < 0:
                return False
            if type(joker.increase) is not int or joker.increase < 0:
                return False
            expected_center = "j_rocket"
        elif type(joker) is ScholarJoker:
            expected_center = "j_scholar"
        elif type(joker) is SeanceJoker:
            expected_center = "j_seance"
        elif type(joker) is ScaryFaceJoker:
            expected_center = "j_scary_face"
        elif type(joker) is SlyJoker:
            expected_center = "j_sly"
        elif type(joker) is SplashJoker:
            expected_center = "j_splash"
        elif type(joker) is SmileyFaceJoker:
            expected_center = "j_smiley"
        elif type(joker) is CastleJoker:
            if (
                not isinstance(castle_suit, str)
                or castle_suit not in CASTLE_SUITS
                or joker.suit != castle_suit
                or type(joker.chip_mod) is not int
                or joker.chip_mod != 3
                or type(joker.chips) is not int
                or joker.chips < 0
                or joker.chips % 3
            ):
                return False
            expected_center = "j_castle"
        elif type(joker) is VampireJoker:
            if (
                isinstance(joker.x_mult, bool)
                or not isinstance(joker.x_mult, (int, float))
                or not math.isfinite(float(joker.x_mult))
                or float(joker.x_mult) < 1.0
            ):
                return False
            growth_steps = (float(joker.x_mult) - 1.0) / 0.1
            if not math.isclose(
                growth_steps,
                round(growth_steps),
                rel_tol=0.0,
                abs_tol=1e-9,
            ):
                return False
            expected_center = "j_vampire"
        elif type(joker) is WalkieTalkieJoker:
            expected_center = "j_walkie_talkie"
        elif type(joker) is WilyJoker:
            expected_center = "j_wily"
        elif type(joker) is WrathfulJoker:
            expected_center = "j_wrathful_joker"
        elif type(joker) is ZanyJoker:
            expected_center = "j_zany"
        else:
            return False
        if getattr(joker, "center", None) != expected_center:
            return False
        if getattr(joker, "edition", None) is not None:
            return False
        if getattr(joker, "debuffed", False) is not False:
            return False
    return True
