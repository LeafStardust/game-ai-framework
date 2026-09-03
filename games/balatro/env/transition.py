"""First exact R1 headless transition slice.

This module owns environment-private run state that is required for deterministic
simulation but is not part of the canonical public observation.  The initial
transition engine deliberately covers only deterministic shop operations whose
outcomes do not require R2 RNG or unmodeled acquisition side effects.  Joker
acquisition is enabled only for explicitly audited modeled identities; generic
Jokers, vouchers, booster opening, and stochastic transitions remain unavailable
until their exact RNG/state ownership exists.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from games.balatro.card import BalatroCard
from games.balatro.env.actions import EnvAction
from games.balatro.jokers.abstract_joker import AbstractJoker
from games.balatro.jokers.acrobat import AcrobatJoker
from games.balatro.jokers.arrowhead import ArrowheadJoker
from games.balatro.jokers.banner import BannerJoker
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.blackboard import BlackboardJoker
from games.balatro.jokers.blue_joker import BlueJoker
from games.balatro.jokers.clever_joker import CleverJoker
from games.balatro.jokers.crafty_joker import CraftyJoker
from games.balatro.jokers.crazy_joker import CrazyJoker
from games.balatro.jokers.devious_joker import DeviousJoker
from games.balatro.jokers.droll_joker import DrollJoker
from games.balatro.jokers.drunkard import DrunkardJoker
from games.balatro.jokers.even_steven import EvenStevenJoker
from games.balatro.jokers.fibonacci import FibonacciJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.flower_pot import FlowerPotJoker
from games.balatro.jokers.four_fingers import FourFingersJoker
from games.balatro.jokers.gluttonous_joker import GluttonousJoker
from games.balatro.jokers.greedy_joker import GreedyJoker
from games.balatro.jokers.half_joker import HalfJoker
from games.balatro.jokers.joker_stencil import JokerStencil
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.juggler import JugglerJoker
from games.balatro.jokers.lusty_joker import LustyJoker
from games.balatro.jokers.mad_joker import MadJoker
from games.balatro.jokers.merry_andy import MerryAndyJoker
from games.balatro.jokers.mystic_summit import MysticSummitJoker
from games.balatro.jokers.odd_todd import OddToddJoker
from games.balatro.jokers.onyx_agate import OnyxAgateJoker
from games.balatro.jokers.pareidolia import PareidoliaJoker
from games.balatro.jokers.photograph import PhotographJoker
from games.balatro.jokers.raised_fist import RaisedFistJoker
from games.balatro.jokers.scary_face import ScaryFaceJoker
from games.balatro.jokers.scholar import ScholarJoker
from games.balatro.jokers.seeing_double import SeeingDoubleJoker
from games.balatro.jokers.shoot_the_moon import ShootTheMoonJoker
from games.balatro.jokers.shortcut import ShortcutJoker
from games.balatro.jokers.sly_joker import SlyJoker
from games.balatro.jokers.smeared_joker import SmearedJoker
from games.balatro.jokers.smiley_face import SmileyFaceJoker
from games.balatro.jokers.splash import SplashJoker
from games.balatro.jokers.stuntman import StuntmanJoker
from games.balatro.jokers.the_duo import TheDuoJoker
from games.balatro.jokers.the_family import TheFamilyJoker
from games.balatro.jokers.the_order import TheOrderJoker
from games.balatro.jokers.the_tribe import TheTribeJoker
from games.balatro.jokers.the_trio import TheTrioJoker
from games.balatro.jokers.triboulet import TribouletJoker
from games.balatro.jokers.troubadour import TroubadourJoker
from games.balatro.jokers.walkie_talkie import WalkieTalkieJoker
from games.balatro.jokers.wily_joker import WilyJoker
from games.balatro.jokers.wrathful_joker import WrathfulJoker
from games.balatro.jokers.zany_joker import ZanyJoker
from games.balatro.state import BalatroState


_EXACT_R1_JOKER_ACQUISITION_TYPES = (
    FlatMultJoker,
    AbstractJoker,
    AcrobatJoker,
    BannerJoker,
    BaronJoker,
    BlackboardJoker,
    BlueJoker,
    EvenStevenJoker,
    FibonacciJoker,
    HalfJoker,
    MysticSummitJoker,
    OddToddJoker,
    PhotographJoker,
    RaisedFistJoker,
    ScholarJoker,
    SmileyFaceJoker,
    WalkieTalkieJoker,
    JugglerJoker,
    FourFingersJoker,
    PareidoliaJoker,
    ShortcutJoker,
    SmearedJoker,
    SplashJoker,
    JollyJoker,
    SlyJoker,
    ZanyJoker,
    WilyJoker,
    TheDuoJoker,
    CrazyJoker,
    DeviousJoker,
    DrollJoker,
    CraftyJoker,
    MadJoker,
    CleverJoker,
    TheTrioJoker,
    TheFamilyJoker,
    TheOrderJoker,
    TheTribeJoker,
    GreedyJoker,
    LustyJoker,
    WrathfulJoker,
    GluttonousJoker,
    ScaryFaceJoker,
    ArrowheadJoker,
    OnyxAgateJoker,
    FlowerPotJoker,
    SeeingDoubleJoker,
    JokerStencil,
    ShootTheMoonJoker,
    TribouletJoker,
)


class HeadlessTransitionError(ValueError):
    """Raised when a requested headless transition is not exact/legal."""


@dataclass
class HeadlessRunState:
    """Exact environment-owned state around the canonical public observation.

    ``public`` remains the single source of truth for information visible to the
    policy.  The other fields are simulator-owned state needed to make future
    transitions deterministic and replayable without leaking hidden information
    into observations.
    """

    public: BalatroState
    seed: str | int
    rng_state: Any = None
    draw_pile: list[BalatroCard] = field(default_factory=list)
    discard_pile: list[BalatroCard] = field(default_factory=list)
    played_pile: list[BalatroCard] = field(default_factory=list)
    reroll_cost: int = 5
    skips: int = 0
    tags: list[str] = field(default_factory=list)
    pack_choices: list[Any] = field(default_factory=list)

    def __post_init__(self) -> None:
        if str(self.public.deck_name).upper() != "RED":
            raise HeadlessTransitionError("R1 headless state currently supports Red Deck only")
        if str(self.public.stake_name).upper() != "WHITE":
            raise HeadlessTransitionError("R1 headless state currently supports White Stake only")
        self._require_int("money", self.public.money)
        self._require_nonnegative_int("hand_size", self.public.hand_size)
        self._require_nonnegative_int("hands_remaining", self.public.hands_remaining)
        if not isinstance(self.public.round_reset_hands_observed, bool):
            raise HeadlessTransitionError("round_reset_hands_observed must be a boolean")
        if self.public.round_reset_hands_observed:
            self._require_nonnegative_int(
                "round_reset_hands",
                self.public.round_reset_hands,
            )
        self._require_nonnegative_int("discards_remaining", self.public.discards_remaining)
        self._require_nonnegative_int("joker_slots", self.public.joker_slots)
        self._require_nonnegative_int("consumable_slots", self.public.consumable_slots)
        if not isinstance(self.public.round_reset_discards_observed, bool):
            raise HeadlessTransitionError("round_reset_discards_observed must be a boolean")
        if self.public.round_reset_discards_observed:
            self._require_nonnegative_int(
                "round_reset_discards",
                self.public.round_reset_discards,
            )
        self._require_nonnegative_int("reroll_cost", self.reroll_cost)
        self._require_nonnegative_int("skips", self.skips)

    @staticmethod
    def _require_int(name: str, value: Any) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise HeadlessTransitionError(f"{name} must be an exact integer")

    @classmethod
    def _require_nonnegative_int(cls, name: str, value: Any) -> None:
        cls._require_int(name, value)
        if value < 0:
            raise HeadlessTransitionError(f"{name} cannot be negative")

    def copy(self) -> "HeadlessRunState":
        """Return an isolated transition snapshot.

        A deep copy is intentional here: public ``BalatroState.copy`` is shallow
        for several contained gameplay objects, while a simulator transition must
        never mutate the pre-transition state through shared Joker/shop/card
        objects.
        """

        return deepcopy(self)


class ShopTransitionEngine:
    """Exact deterministic transitions for the currently modeled shop subset."""

    def legal_actions(self, run: HeadlessRunState) -> tuple[EnvAction, ...]:
        state = run.public
        if state.phase != "SHOP" or not state.shop_active:
            return ()

        actions: list[EnvAction] = []
        if len(state.jokers) < state.joker_slots:
            actions.extend(
                EnvAction.from_alias("BUY_JOKER", {"slot": slot})
                for slot, item in enumerate(state.shop_jokers)
                if self._joker_acquisition_is_exact(state, item)
                and self._is_affordable(state, item)
            )
        if len(state.consumables) < state.consumable_slots:
            actions.extend(
                EnvAction.from_alias("BUY_CONSUMABLE", {"slot": slot})
                for slot, item in enumerate(state.shop_consumables)
                if self._is_affordable(state, item)
            )

        # Generic BUY_JOKER remains fail-closed.  Only explicitly audited Joker
        # identities admitted by ``_joker_acquisition_is_exact`` are exposed.
        # This prevents list-transfer semantics from silently skipping immediate
        # capacity/resource modifiers on other Jokers.
        #
        # BUY_VOUCHER is intentionally not exposed until the headless state owns
        # the voucher's immediate rule modification.  Merely moving the voucher
        # into ``state.vouchers`` would create a legal transition with incomplete
        # gameplay semantics.
        #
        # OPEN_PACK is also intentionally not exposed here: purchase is
        # deterministic, but entering a generated pack is not exact until R2 owns
        # pack RNG and R1 owns the resulting pack state.
        actions.append(EnvAction.from_alias("END_SHOP"))
        return tuple(actions)

    def step(self, run: HeadlessRunState, action: EnvAction) -> HeadlessRunState:
        if action not in self.legal_actions(run):
            raise HeadlessTransitionError(f"illegal shop transition: {action.alias}")

        next_run = run.copy()
        state = next_run.public
        params = action.payload()

        if action.alias == "END_SHOP":
            state.shop_active = False
            state.phase = "BLIND_SELECT"
            state.shop_jokers.clear()
            state.shop_consumables.clear()
            state.shop_boosters.clear()
            state.shop_vouchers.clear()
            return next_run

        slot = self._slot(params)
        if action.alias == "BUY_JOKER":
            self._buy(state, state.shop_jokers, state.jokers, slot)
            self._apply_joker_acquisition_effects(state, state.jokers[-1])
            return next_run
        if action.alias == "BUY_CONSUMABLE":
            self._buy(state, state.shop_consumables, state.consumables, slot)
            return next_run

        raise HeadlessTransitionError(f"unimplemented shop transition: {action.alias}")

    @staticmethod
    def _joker_acquisition_is_exact(state: BalatroState, item: Any) -> bool:
        """Return whether R1 currently owns this Joker's purchase semantics.

        Most admitted identities have unconditional exact acquisition semantics.
        Resource-sensitive Jokers may additionally require authoritative public
        state. Editions remain fail-closed until their headless ownership is
        audited, because Negative in particular changes Joker capacity semantics.
        """

        if getattr(item, "edition", None):
            return False
        if type(item) in _EXACT_R1_JOKER_ACQUISITION_TYPES:
            return True
        if type(item) is StuntmanJoker:
            # R1 does not guess how live Balatro resolves a capacity modifier
            # larger than the authoritative current hand limit. Keep those edge
            # states unavailable instead of creating a negative headless limit.
            return state.hand_size >= 2
        if type(item) is DrunkardJoker:
            return bool(state.round_reset_discards_observed)
        if type(item) is TroubadourJoker:
            return bool(state.round_reset_hands_observed) and state.round_reset_hands >= 1
        if type(item) is MerryAndyJoker:
            return bool(state.round_reset_discards_observed) and state.hand_size >= 1
        return False

    @staticmethod
    def _apply_joker_acquisition_effects(state: BalatroState, joker: Any) -> None:
        """Apply exact immediate persistent state changes for audited Jokers.

        ``BalatroState.hand_size`` is canonical public hand capacity. Likewise,
        ``round_reset_hands`` and ``round_reset_discards`` are explicitly the
        public starting allowances for the next round, distinct from the finished
        blind's current remaining resources. SELL_JOKER stays outside the frozen
        training surface until inverse lifecycle transitions are independently
        audited.
        """

        if type(joker) is JugglerJoker:
            state.hand_size += 1
        elif type(joker) is StuntmanJoker:
            state.hand_size -= 2
        elif type(joker) is DrunkardJoker:
            state.round_reset_discards += 1
        elif type(joker) is TroubadourJoker:
            state.hand_size += 2
            state.round_reset_hands -= 1
        elif type(joker) is MerryAndyJoker:
            state.hand_size -= 1
            state.round_reset_discards += 3

    @classmethod
    def _is_affordable(cls, state: BalatroState, item: Any) -> bool:
        """Return exact purchase affordability without inventing missing prices."""

        try:
            price = cls._price(item)
        except HeadlessTransitionError:
            return False
        return price >= 0 and state.money >= price

    @classmethod
    def _buy(cls, state: BalatroState, source: list, destination: list, slot: int) -> None:
        if slot < 0 or slot >= len(source):
            raise HeadlessTransitionError(f"shop slot out of range: {slot}")
        item = source[slot]
        price = cls._price(item)
        if price < 0 or state.money < price:
            raise HeadlessTransitionError("shop item is not affordable")
        state.money -= price
        destination.append(source.pop(slot))

    @staticmethod
    def _slot(params: dict[str, Any]) -> int:
        value = params.get("slot")
        if isinstance(value, bool):
            raise HeadlessTransitionError("shop slot must be an integer")
        try:
            slot = int(value)
        except (TypeError, ValueError) as exc:
            raise HeadlessTransitionError("shop action requires integer slot") from exc
        if slot != value and not isinstance(value, int):
            raise HeadlessTransitionError("shop slot must be an integer")
        return slot

    @staticmethod
    def _price(item: Any) -> int:
        value = getattr(item, "price", None)
        if value is None:
            value = getattr(item, "cost", None)
        if isinstance(value, dict):
            value = value.get("buy")
        if isinstance(value, bool) or not isinstance(value, int):
            raise HeadlessTransitionError("shop item has no exact integer price")
        return value
