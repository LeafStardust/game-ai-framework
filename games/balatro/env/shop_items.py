"""Canonical headless representations for generated shop inventory.

A generated shop Joker is not automatically a mechanically executable Joker
instance.  Shop generation first owns public item identity, rarity, edition, and
purchase price.  Strategy/runtime Joker construction and acquisition semantics are
separate boundaries and remain fail-closed independently.
"""

from __future__ import annotations

from dataclasses import dataclass

from games.balatro.env.shop_joker_generation import OrdinaryShopJokerDescriptor
from games.balatro.env.shop_pricing import (
    price_base_shop_joker_descriptor,
    vanilla_card_sell_cost,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.env.voucher_capabilities import expected_main_shop_slots_for_vouchers
from games.balatro.joker import Joker
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
from games.balatro.jokers.runner import RunnerJoker
from games.balatro.jokers.sixth_sense import SixthSenseJoker
from games.balatro.jokers.supernova import SupernovaJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.jokers.madness import MadnessJoker
from games.balatro.jokers.dna import DNAJoker
from games.balatro.jokers.faceless_joker import FacelessJoker
from games.balatro.jokers.green_joker import GreenJoker
from games.balatro.jokers.midas_mask import MidasMaskJoker
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


@dataclass(frozen=True)
class GeneratedShopJokerItem:
    """Exact public shop metadata for one generated ordinary Joker card."""

    center_key: str
    rarity: int
    base_cost: int
    edition: str | None
    price: int
    discovered: bool | None = None

    @property
    def kind(self) -> str:
        return "JOKER"

    @property
    def center(self) -> str:
        return self.center_key


def materialize_generated_shop_joker_for_acquisition(
    item: GeneratedShopJokerItem,
    *,
    castle_suit: str | None = None,
) -> Joker:
    """Construct the first exactly owned generated gameplay Joker.

    Only explicitly audited vanilla center identities are admitted. Every other
    generated center stays metadata-only until its runtime mechanics and
    lifecycle are independently owned.
    """
    if type(item) is not GeneratedShopJokerItem:
        raise TypeError("item must be an exact GeneratedShopJokerItem")
    if item.center_key == "j_abstract":
        joker_type = AbstractJoker
        expected_rarity = 1
        expected_base_cost = 4
        label = "Abstract Joker"
    elif item.center_key == "j_banner":
        joker_type = BannerJoker
        expected_rarity = 1
        expected_base_cost = 5
        label = "Banner"
    elif item.center_key == "j_joker":
        joker_type = FlatMultJoker
        expected_rarity = 1
        expected_base_cost = 2
        label = "Joker"
    elif item.center_key == "j_blue_joker":
        joker_type = BlueJoker
        expected_rarity = 1
        expected_base_cost = 5
        label = "Blue Joker"
    elif item.center_key == "j_bull":
        joker_type = BullJoker
        expected_rarity = 2
        expected_base_cost = 6
        label = "Bull"
    elif item.center_key == "j_clever":
        joker_type = CleverJoker
        expected_rarity = 1
        expected_base_cost = 4
        label = "Clever Joker"
    elif item.center_key == "j_cloud_9":
        joker_type = Cloud9Joker
        expected_rarity = 2
        expected_base_cost = 7
        label = "Cloud 9"
    elif item.center_key == "j_crazy":
        joker_type = CrazyJoker
        expected_rarity = 1
        expected_base_cost = 4
        label = "Crazy Joker"
    elif item.center_key == "j_crafty":
        joker_type = CraftyJoker
        expected_rarity = 1
        expected_base_cost = 4
        label = "Crafty Joker"
    elif item.center_key == "j_devious":
        joker_type = DeviousJoker
        expected_rarity = 1
        expected_base_cost = 4
        label = "Devious Joker"
    elif item.center_key == "j_droll":
        joker_type = DrollJoker
        expected_rarity = 1
        expected_base_cost = 4
        label = "Droll Joker"
    elif item.center_key == "j_drunkard":
        joker_type = DrunkardJoker
        expected_rarity = 1
        expected_base_cost = 4
        label = "Drunkard"
    elif item.center_key == "j_even_steven":
        joker_type = EvenStevenJoker
        expected_rarity = 1
        expected_base_cost = 4
        label = "Even Steven"
    elif item.center_key == "j_fibonacci":
        joker_type = FibonacciJoker
        expected_rarity = 2
        expected_base_cost = 8
        label = "Fibonacci"
    elif item.center_key == "j_gluttenous_joker":
        joker_type = GluttonousJoker
        expected_rarity = 1
        expected_base_cost = 5
        label = "Gluttonous Joker"
    elif item.center_key == "j_golden":
        joker_type = GoldenJoker
        expected_rarity = 1
        expected_base_cost = 6
        label = "Golden Joker"
    elif item.center_key == "j_green_joker":
        joker_type = GreenJoker
        expected_rarity = 1
        expected_base_cost = 4
        label = "Green Joker"
    elif item.center_key == "j_greedy_joker":
        joker_type = GreedyJoker
        expected_rarity = 1
        expected_base_cost = 5
        label = "Greedy Joker"
    elif item.center_key == "j_half":
        joker_type = HalfJoker
        expected_rarity = 1
        expected_base_cost = 5
        label = "Half Joker"
    elif item.center_key == "j_jolly":
        joker_type = JollyJoker
        expected_rarity = 1
        expected_base_cost = 3
        label = "Jolly Joker"
    elif item.center_key == "j_juggler":
        joker_type = JugglerJoker
        expected_rarity = 1
        expected_base_cost = 4
        label = "Juggler"
    elif item.center_key == "j_lusty_joker":
        joker_type = LustyJoker
        expected_rarity = 1
        expected_base_cost = 5
        label = "Lusty Joker"
    elif item.center_key == "j_mad":
        joker_type = MadJoker
        expected_rarity = 1
        expected_base_cost = 4
        label = "Mad Joker"
    elif item.center_key == "j_mystic_summit":
        joker_type = MysticSummitJoker
        expected_rarity = 1
        expected_base_cost = 5
        label = "Mystic Summit"
    elif item.center_key == "j_mime":
        joker_type = MimeJoker
        expected_rarity = 2
        expected_base_cost = 5
        label = "Mime"
    elif item.center_key == "j_madness":
        joker_type = MadnessJoker
        expected_rarity = 2
        expected_base_cost = 7
        label = "Madness"
    elif item.center_key == "j_dna":
        joker_type = DNAJoker
        expected_rarity = 3
        expected_base_cost = 8
        label = "DNA"
    elif item.center_key == "j_faceless":
        joker_type = FacelessJoker
        expected_rarity = 1
        expected_base_cost = 4
        label = "Faceless Joker"
    elif item.center_key == "j_midas_mask":
        joker_type = MidasMaskJoker
        expected_rarity = 2
        expected_base_cost = 7
        label = "Midas Mask"
    elif item.center_key == "j_odd_todd":
        joker_type = OddToddJoker
        expected_rarity = 1
        expected_base_cost = 4
        label = "Odd Todd"
    elif item.center_key == "j_photograph":
        joker_type = PhotographJoker
        expected_rarity = 1
        expected_base_cost = 5
        label = "Photograph"
    elif item.center_key == "j_raised_fist":
        joker_type = RaisedFistJoker
        expected_rarity = 1
        expected_base_cost = 5
        label = "Raised Fist"
    elif item.center_key == "j_rocket":
        joker_type = RocketJoker
        expected_rarity = 2
        expected_base_cost = 6
        label = "Rocket"
    elif item.center_key == "j_runner":
        joker_type = RunnerJoker
        expected_rarity = 1
        expected_base_cost = 5
        label = "Runner"
    elif item.center_key == "j_scholar":
        joker_type = ScholarJoker
        expected_rarity = 1
        expected_base_cost = 4
        label = "Scholar"
    elif item.center_key == "j_seance":
        joker_type = SeanceJoker
        expected_rarity = 2
        expected_base_cost = 6
        label = "Seance"
    elif item.center_key == "j_scary_face":
        joker_type = ScaryFaceJoker
        expected_rarity = 1
        expected_base_cost = 4
        label = "Scary Face"
    elif item.center_key == "j_splash":
        joker_type = SplashJoker
        expected_rarity = 1
        expected_base_cost = 3
        label = "Splash"
    elif item.center_key == "j_sixth_sense":
        joker_type = SixthSenseJoker
        expected_rarity = 2
        expected_base_cost = 6
        label = "Sixth Sense"
    elif item.center_key == "j_sly":
        joker_type = SlyJoker
        expected_rarity = 1
        expected_base_cost = 3
        label = "Sly Joker"
    elif item.center_key == "j_smiley":
        joker_type = SmileyFaceJoker
        expected_rarity = 1
        expected_base_cost = 4
        label = "Smiley Face"
    elif item.center_key == "j_castle":
        if not isinstance(castle_suit, str) or castle_suit not in CASTLE_SUITS:
            raise HeadlessTransitionError("generated Castle requires the exact round suit")
        joker_type = CastleJoker
        expected_rarity = 2
        expected_base_cost = 6
        label = "Castle"
    elif item.center_key == "j_supernova":
        joker_type = SupernovaJoker
        expected_rarity = 1
        expected_base_cost = 5
        label = "Supernova"
    elif item.center_key == "j_vampire":
        joker_type = VampireJoker
        expected_rarity = 2
        expected_base_cost = 7
        label = "Vampire"
    elif item.center_key == "j_walkie_talkie":
        joker_type = WalkieTalkieJoker
        expected_rarity = 1
        expected_base_cost = 4
        label = "Walkie Talkie"
    elif item.center_key == "j_wily":
        joker_type = WilyJoker
        expected_rarity = 1
        expected_base_cost = 4
        label = "Wily Joker"
    elif item.center_key == "j_wrathful_joker":
        joker_type = WrathfulJoker
        expected_rarity = 1
        expected_base_cost = 5
        label = "Wrathful Joker"
    elif item.center_key == "j_zany":
        joker_type = ZanyJoker
        expected_rarity = 1
        expected_base_cost = 4
        label = "Zany Joker"
    else:
        raise HeadlessTransitionError("generated Joker center is not materializable")
    if type(item.rarity) is not int or item.rarity != expected_rarity:
        raise HeadlessTransitionError("generated Joker rarity must be exact")
    if type(item.base_cost) is not int or item.base_cost != expected_base_cost:
        raise HeadlessTransitionError("generated Joker base cost must be exact")
    if item.edition is not None:
        raise HeadlessTransitionError("generated Joker edition is not materializable")
    if type(item.price) is not int or item.price < 1:
        raise HeadlessTransitionError("generated Joker price must be exact")
    if not isinstance(item.discovered, bool):
        raise HeadlessTransitionError("generated Joker discovery state must be exact")

    joker = CastleJoker(castle_suit) if joker_type is CastleJoker else joker_type()
    joker.center = item.center_key
    joker.label = label
    joker.rarity = item.rarity
    joker.edition = None
    joker.base_cost = item.base_cost
    joker.cost = item.price
    joker.sell_cost = vanilla_card_sell_cost(item.price)
    # Vanilla ``Card:add_to_deck`` discovers the center as part of acquisition.
    joker.discovered = True
    joker.eternal = False
    return joker


def materialize_shop_joker_descriptor(
    descriptor: OrdinaryShopJokerDescriptor,
) -> tuple[HeadlessRunState, GeneratedShopJokerItem]:
    """Materialize exact public metadata without constructing a gameplay Joker.

    The returned run is the descriptor's post-generation snapshot.  It is copied
    so later inventory insertion cannot mutate the descriptor's retained replay
    state.  This function intentionally does not append the item to ``shop_jokers``
    and does not make BUY_JOKER legal.
    """
    if not isinstance(descriptor, OrdinaryShopJokerDescriptor):
        raise TypeError("descriptor must be OrdinaryShopJokerDescriptor")

    center_key = descriptor.center_key
    if not isinstance(center_key, str) or not center_key:
        raise HeadlessTransitionError("generated Joker center key must be nonempty")
    if type(descriptor.rarity) is not int or descriptor.rarity not in (1, 2, 3):
        raise HeadlessTransitionError("generated Joker rarity must be exact 1, 2, or 3")
    if type(descriptor.base_cost) is not int or descriptor.base_cost < 0:
        raise HeadlessTransitionError("generated Joker base cost must be a nonnegative exact integer")

    price = price_base_shop_joker_descriptor(descriptor)
    item = GeneratedShopJokerItem(
        center_key=center_key,
        rarity=descriptor.rarity,
        base_cost=descriptor.base_cost,
        edition=descriptor.edition,
        price=price,
        discovered=descriptor.run.generated_center_discovered(center_key),
    )
    return descriptor.run.copy(), item


def insert_generated_shop_joker_item(
    run: HeadlessRunState,
    item: GeneratedShopJokerItem,
) -> HeadlessRunState:
    """Insert one exact generated Joker card into the public main-shop area.

    The canonical state stores main-shop Jokers and consumables in category-specific
    lists, so shared main-shop capacity is enforced across their sum. Voucher-derived
    capacity is owned by ``voucher_capabilities`` rather than duplicated here. This
    operation owns placement only; it intentionally does not convert the metadata
    item into a gameplay Joker and therefore does not widen BUY_JOKER legality.
    """
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")
    if not isinstance(item, GeneratedShopJokerItem):
        raise TypeError("item must be GeneratedShopJokerItem")
    state = run.public
    if state.phase != "SHOP" or not state.shop_active:
        raise HeadlessTransitionError("generated shop insertion requires active SHOP")
    capacity = expected_main_shop_slots_for_vouchers(state)
    if capacity is None:
        raise HeadlessTransitionError("main shop capacity is not exact")
    occupied = len(state.shop_jokers) + len(state.shop_consumables)
    if occupied >= capacity:
        raise HeadlessTransitionError("main shop inventory is already full")

    next_run = run.copy()
    next_run.public.shop_jokers.append(item)
    return next_run
