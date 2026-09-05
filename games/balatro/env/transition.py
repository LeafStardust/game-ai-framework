"""First exact R1 headless transition slice.

This module owns environment-private run state that is required for deterministic
simulation but is not part of the canonical public observation.  The initial
transition engine deliberately covers only deterministic shop operations whose
outcomes do not require unowned RNG or acquisition side effects.  Joker and
Voucher acquisition are enabled only for explicitly audited identities; unknown
or lifecycle-incomplete purchases remain unavailable.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from games.balatro.card import BalatroCard
from games.balatro.deck_rules import starting_deck_size_for_name
from games.balatro.env.actions import EnvAction
from games.balatro.env.blind_progression import BlindProgressionState
from games.balatro.env.card_order import (
    derive_playing_card_order,
    playing_card_order_matches,
)
from games.balatro.env.joker_order import JokerOrderError, JokerOrderState
from games.balatro.env.rng import BalatroRNG
from games.balatro.env.voucher_capabilities import (
    EXACT_ANTE_VOUCHER_KEYS,
    EXACT_DISCOUNT_VOUCHER_KEYS,
    EXACT_EDITION_RATE_VOUCHER_KEYS,
    EXACT_INTEREST_CAP_VOUCHER_KEYS,
    EXACT_REROLL_COST_VOUCHER_KEYS,
    EXACT_SHOP_SIZE_VOUCHER_KEYS,
    EXACT_SHOP_TYPE_RATE_VOUCHER_KEYS,
)
from games.balatro.jokers.abstract_joker import AbstractJoker
from games.balatro.jokers.acrobat import AcrobatJoker
from games.balatro.jokers.arrowhead import ArrowheadJoker
from games.balatro.jokers.banner import BannerJoker
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.blackboard import BlackboardJoker
from games.balatro.jokers.blue_joker import BlueJoker
from games.balatro.jokers.bootstraps import BootstrapsJoker
from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.clever_joker import CleverJoker
from games.balatro.jokers.crafty_joker import CraftyJoker
from games.balatro.jokers.crazy_joker import CrazyJoker
from games.balatro.jokers.devious_joker import DeviousJoker
from games.balatro.jokers.drivers_license import DriversLicenseJoker
from games.balatro.jokers.droll_joker import DrollJoker
from games.balatro.jokers.drunkard import DrunkardJoker
from games.balatro.jokers.dusk import DuskJoker
from games.balatro.jokers.erosion import ErosionJoker
from games.balatro.jokers.even_steven import EvenStevenJoker
from games.balatro.jokers.fibonacci import FibonacciJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.flower_pot import FlowerPotJoker
from games.balatro.jokers.four_fingers import FourFingersJoker
from games.balatro.jokers.gluttonous_joker import GluttonousJoker
from games.balatro.jokers.greedy_joker import GreedyJoker
from games.balatro.jokers.hack import HackJoker
from games.balatro.jokers.half_joker import HalfJoker
from games.balatro.jokers.hanging_chad import HangingChadJoker
from games.balatro.jokers.joker_stencil import JokerStencil
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.juggler import JugglerJoker
from games.balatro.jokers.lusty_joker import LustyJoker
from games.balatro.jokers.mad_joker import MadJoker
from games.balatro.jokers.merry_andy import MerryAndyJoker
from games.balatro.jokers.mime import MimeJoker
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
from games.balatro.jokers.sock_and_buskin import SockAndBuskinJoker
from games.balatro.jokers.splash import SplashJoker
from games.balatro.jokers.steel_joker import SteelJoker
from games.balatro.jokers.stone_joker import StoneJoker
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
    BullJoker,
    BootstrapsJoker,
    DuskJoker,
    HackJoker,
    HangingChadJoker,
    MimeJoker,
    SockAndBuskinJoker,
)

_OWNED_DECK_SCORING_TYPES = (
    DriversLicenseJoker,
    ErosionJoker,
    SteelJoker,
    StoneJoker,
)

_EXACT_RESOURCE_VOUCHER_KEYS = frozenset(
    {
        "v_crystal_ball",
        "v_grabber",
        "v_nacho_tong",
        "v_wasteful",
        "v_recyclomancy",
        "v_antimatter",
        "v_paint_brush",
        "v_palette",
    }
)

_HAND_ALLOWANCE_VOUCHER_KEYS = frozenset({"v_grabber", "v_nacho_tong"})
_DISCARD_ALLOWANCE_VOUCHER_KEYS = frozenset({"v_wasteful", "v_recyclomancy"})


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
    rng_state: BalatroRNG | dict[str, Any] | None = None
    playing_card_order: list[BalatroCard] | None = None
    joker_order_state: JokerOrderState | None = None
    blind_progression_state: BlindProgressionState | None = None
    draw_pile: list[BalatroCard] = field(default_factory=list)
    discard_pile: list[BalatroCard] = field(default_factory=list)
    played_pile: list[BalatroCard] = field(default_factory=list)
    round_bonus_hands: int = 0
    round_bonus_discards: int = 0
    boss_hands_sub: int | None = None
    boss_discards_sub: int | None = None
    boss_hand_size_sub: int | None = None
    base_reroll_cost: int = 5
    reroll_cost: int = 5
    skips: int = 0
    tags: list[str] = field(default_factory=list)
    pack_choices: list[Any] = field(default_factory=list)
    pack_return_phase: str | None = None

    def __post_init__(self) -> None:
        if str(self.public.deck_name).upper() != "RED":
            raise HeadlessTransitionError("R1 headless state currently supports Red Deck only")
        if str(self.public.stake_name).upper() != "WHITE":
            raise HeadlessTransitionError("R1 headless state currently supports White Stake only")
        if isinstance(self.seed, bool) or not isinstance(self.seed, (str, int)):
            raise HeadlessTransitionError("seed must be a string or exact integer")

        if self.rng_state is None:
            self.rng_state = BalatroRNG(self.seed)
        elif isinstance(self.rng_state, dict):
            try:
                self.rng_state = BalatroRNG.from_snapshot(self.rng_state)
            except (TypeError, ValueError) as exc:
                raise HeadlessTransitionError("invalid Balatro RNG snapshot") from exc
        elif not isinstance(self.rng_state, BalatroRNG):
            raise HeadlessTransitionError(
                "rng_state must be BalatroRNG, an exact RNG snapshot, or None"
            )
        if self.rng_state.seed != str(self.seed):
            raise HeadlessTransitionError("rng_state seed does not match headless run seed")

        self._require_int("money", self.public.money)
        self._require_nonnegative_int("hand_size", self.public.hand_size)
        self._require_nonnegative_int("hands_remaining", self.public.hands_remaining)
        if not isinstance(self.public.round_reset_hands_observed, bool):
            raise HeadlessTransitionError("round_reset_hands_observed must be a boolean")
        if self.public.round_reset_hands_observed:
            self._require_nonnegative_int("round_reset_hands", self.public.round_reset_hands)
        self._require_nonnegative_int("discards_remaining", self.public.discards_remaining)
        self._require_nonnegative_int("joker_slots", self.public.joker_slots)
        self._require_nonnegative_int("consumable_slots", self.public.consumable_slots)
        if not isinstance(self.public.round_reset_discards_observed, bool):
            raise HeadlessTransitionError("round_reset_discards_observed must be a boolean")
        if self.public.round_reset_discards_observed:
            self._require_nonnegative_int("round_reset_discards", self.public.round_reset_discards)
        if not isinstance(self.public.vouchers, list):
            raise HeadlessTransitionError("vouchers must be a list")
        if any(not isinstance(key, str) or not key for key in self.public.vouchers):
            raise HeadlessTransitionError("vouchers must contain non-empty center keys")
        if len(self.public.vouchers) != len(set(self.public.vouchers)):
            raise HeadlessTransitionError("vouchers must not contain duplicate center keys")
        self._require_int("round_bonus_hands", self.round_bonus_hands)
        self._require_int("round_bonus_discards", self.round_bonus_discards)

        if self.blind_progression_state is not None and not isinstance(
            self.blind_progression_state, BlindProgressionState
        ):
            raise HeadlessTransitionError(
                "blind_progression_state must be BlindProgressionState or None"
            )

        if self.boss_hands_sub is not None:
            self._require_int("boss_hands_sub", self.boss_hands_sub)
            if self.public.boss_name != "The Needle":
                raise HeadlessTransitionError("boss_hands_sub is only valid for The Needle")
        if self.boss_discards_sub is not None:
            self._require_nonnegative_int("boss_discards_sub", self.boss_discards_sub)
            if self.public.boss_name != "The Water":
                raise HeadlessTransitionError("boss_discards_sub is only valid for The Water")
        if self.boss_hand_size_sub is not None:
            self._require_nonnegative_int("boss_hand_size_sub", self.boss_hand_size_sub)
            if self.public.boss_name != "The Manacle":
                raise HeadlessTransitionError("boss_hand_size_sub is only valid for The Manacle")
        if sum(
            value is not None
            for value in (self.boss_hands_sub, self.boss_discards_sub, self.boss_hand_size_sub)
        ) > 1:
            raise HeadlessTransitionError(
                "only one reversible boss resource adjustment may be active"
            )

        if self.public.owned_deck is not None:
            if not isinstance(self.public.owned_deck, list):
                raise HeadlessTransitionError("owned_deck must be a list or None")
            if any(not isinstance(card, BalatroCard) for card in self.public.owned_deck):
                raise HeadlessTransitionError("owned_deck must contain only BalatroCard values")

        if self.playing_card_order is None:
            self.playing_card_order = derive_playing_card_order(self.public)
        else:
            if not isinstance(self.playing_card_order, list):
                raise HeadlessTransitionError("playing_card_order must be a list or None")
            if any(not isinstance(card, BalatroCard) for card in self.playing_card_order):
                raise HeadlessTransitionError(
                    "playing_card_order must contain only BalatroCard values"
                )
            if not playing_card_order_matches(self.playing_card_order, self.public):
                raise HeadlessTransitionError(
                    "playing_card_order must reference the authoritative owned cards exactly"
                )

        if self.joker_order_state is None:
            self.joker_order_state = JokerOrderState.from_public(self.public.jokers)
        else:
            if not isinstance(self.joker_order_state, JokerOrderState):
                raise HeadlessTransitionError("joker_order_state must be JokerOrderState or None")
            try:
                self.joker_order_state.validate_against(self.public.jokers)
            except JokerOrderError as exc:
                raise HeadlessTransitionError("invalid retained Joker order state") from exc

        for zone_name in ("draw_pile", "discard_pile", "played_pile"):
            zone = getattr(self, zone_name)
            if not isinstance(zone, list):
                raise HeadlessTransitionError(f"{zone_name} must be a list")
            if any(not isinstance(card, BalatroCard) for card in zone):
                raise HeadlessTransitionError(
                    f"{zone_name} must contain only BalatroCard values"
                )
        if not isinstance(self.tags, list):
            raise HeadlessTransitionError("tags must be a list")
        if any(not isinstance(tag, str) for tag in self.tags):
            raise HeadlessTransitionError("tags must contain only strings")
        if not isinstance(self.pack_choices, list):
            raise HeadlessTransitionError("pack_choices must be a list")
        if self.pack_return_phase not in {None, "SHOP", "BLIND_SELECT"}:
            raise HeadlessTransitionError(
                "pack_return_phase must be SHOP, BLIND_SELECT, or None"
            )
        self._require_nonnegative_int("base_reroll_cost", self.base_reroll_cost)
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

    @property
    def rng(self) -> BalatroRNG:
        if not isinstance(self.rng_state, BalatroRNG):
            raise HeadlessTransitionError("headless RNG owner is unavailable")
        return self.rng_state

    def rng_snapshot(self) -> dict[str, Any]:
        return self.rng.snapshot()

    def require_playing_card_order(self) -> list[BalatroCard]:
        if self.playing_card_order is None:
            raise HeadlessTransitionError(
                "exact playing-card creation order is unavailable for shuffle"
            )
        if not playing_card_order_matches(self.playing_card_order, self.public):
            raise HeadlessTransitionError(
                "playing-card creation order is stale relative to the public deck"
            )
        return list(self.playing_card_order)

    def require_joker_order_state(self) -> JokerOrderState:
        if self.joker_order_state is None:
            raise HeadlessTransitionError("exact Joker creation order is unavailable")
        try:
            self.joker_order_state.validate_against(self.public.jokers)
        except JokerOrderError as exc:
            raise HeadlessTransitionError(
                "retained Joker order is stale relative to owned Jokers"
            ) from exc
        return self.joker_order_state

    def require_blind_progression_state(self) -> BlindProgressionState:
        if self.blind_progression_state is None:
            raise HeadlessTransitionError("exact blind progression state is unavailable")
        return self.blind_progression_state

    def copy(self) -> "HeadlessRunState":
        return deepcopy(self)


class ShopTransitionEngine:
    """Exact deterministic transitions for the currently modeled shop subset."""

    def legal_actions(self, run: HeadlessRunState) -> tuple[EnvAction, ...]:
        state = run.public
        if state.phase != "SHOP" or not state.shop_active:
            return ()
        actions: list[EnvAction] = []
        from games.balatro.env.joker_sale import can_sell_joker_exact

        actions.extend(
            EnvAction.from_alias("SELL_JOKER", {"joker_index": joker_index})
            for joker_index in range(len(state.jokers))
            if can_sell_joker_exact(run, joker_index)
        )
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
        actions.extend(
            EnvAction.from_alias("BUY_VOUCHER", {"slot": slot})
            for slot, item in enumerate(state.shop_vouchers)
            if self._voucher_redemption_is_exact(run, item, slot)
            and self._is_affordable(state, item)
        )
        actions.append(EnvAction.from_alias("END_SHOP"))
        return tuple(actions)

    def step(self, run: HeadlessRunState, action: EnvAction) -> HeadlessRunState:
        if action not in self.legal_actions(run):
            raise HeadlessTransitionError(f"illegal shop transition: {action.alias}")
        next_run = run.copy()
        state = next_run.public
        params = action.payload()

        if action.alias == "SELL_JOKER":
            from games.balatro.env.joker_sale import sell_joker_exact

            joker_index = params.get("joker_index")
            if isinstance(joker_index, bool) or not isinstance(joker_index, int):
                raise HeadlessTransitionError("Joker sale requires integer joker_index")
            return sell_joker_exact(run, joker_index)

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
            purchased = state.shop_jokers[slot]
            if next_run.joker_order_state is not None:
                try:
                    next_run.joker_order_state.acquire(purchased, state.jokers)
                except JokerOrderError as exc:
                    raise HeadlessTransitionError(
                        "cannot retain exact Joker order for purchase"
                    ) from exc
            self._buy(state, state.shop_jokers, state.jokers, slot)
            self._apply_joker_acquisition_effects(state, state.jokers[-1])
            return next_run
        if action.alias == "BUY_CONSUMABLE":
            self._buy(state, state.shop_consumables, state.consumables, slot)
            return next_run
        if action.alias == "BUY_VOUCHER":
            item = state.shop_vouchers[slot]
            key = self._voucher_key(item)
            if not self._voucher_redemption_is_exact(next_run, item, slot):
                raise HeadlessTransitionError("Voucher redemption effect is not exact")
            if key in EXACT_ANTE_VOUCHER_KEYS:
                from games.balatro.env.ante_voucher_redemption import redeem_exact_ante_voucher
                return redeem_exact_ante_voucher(next_run, slot=slot)
            if key in EXACT_DISCOUNT_VOUCHER_KEYS:
                from games.balatro.env.discount_voucher_redemption import redeem_exact_discount_voucher
                return redeem_exact_discount_voucher(next_run, slot)
            if key in EXACT_SHOP_TYPE_RATE_VOUCHER_KEYS:
                from games.balatro.env.shop_type_rate_voucher_redemption import redeem_exact_shop_type_rate_voucher
                return redeem_exact_shop_type_rate_voucher(next_run, slot)
            if key in EXACT_REROLL_COST_VOUCHER_KEYS:
                from games.balatro.env.reroll_voucher_redemption import redeem_exact_reroll_voucher
                return redeem_exact_reroll_voucher(next_run, slot)
            if key in EXACT_INTEREST_CAP_VOUCHER_KEYS:
                from games.balatro.env.interest_cap_voucher_redemption import redeem_exact_interest_cap_voucher
                return redeem_exact_interest_cap_voucher(next_run, slot)
            if key in EXACT_SHOP_SIZE_VOUCHER_KEYS:
                from games.balatro.env.shop_size_voucher_redemption import redeem_exact_shop_size_voucher
                return redeem_exact_shop_size_voucher(next_run, slot)
            price = self._price(item)
            if price < 0 or state.money < price:
                raise HeadlessTransitionError("shop item is not affordable")
            state.money -= price
            state.shop_vouchers.pop(slot)
            state.vouchers.append(key)
            self._apply_voucher_redemption_effects(state, key)
            return next_run
        raise HeadlessTransitionError(f"unimplemented shop transition: {action.alias}")

    @staticmethod
    def _joker_acquisition_is_exact(state: BalatroState, item: Any) -> bool:
        if getattr(item, "edition", None):
            return False
        if type(item) in _EXACT_R1_JOKER_ACQUISITION_TYPES:
            return True
        if type(item) in _OWNED_DECK_SCORING_TYPES:
            if state.owned_deck is None:
                return False
            if type(item) is ErosionJoker:
                return starting_deck_size_for_name(state.deck_name) is not None
            return True
        if type(item) is StuntmanJoker:
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
    def _voucher_redemption_is_exact(
        cls, run: HeadlessRunState, item: Any, slot: int
    ) -> bool:
        state = run.public
        try:
            key = cls._voucher_key(item)
        except HeadlessTransitionError:
            return False
        if key in EXACT_ANTE_VOUCHER_KEYS:
            from games.balatro.env.ante_voucher_redemption import ante_voucher_redemption_is_exact
            return ante_voucher_redemption_is_exact(run, slot=slot)
        if key in EXACT_DISCOUNT_VOUCHER_KEYS:
            from games.balatro.env.discount_voucher_redemption import discount_voucher_redemption_is_exact
            return discount_voucher_redemption_is_exact(run, slot)
        if key in EXACT_SHOP_TYPE_RATE_VOUCHER_KEYS:
            from games.balatro.env.shop_type_rate_voucher_redemption import shop_type_rate_voucher_redemption_is_exact
            return shop_type_rate_voucher_redemption_is_exact(run, slot)
        if key in EXACT_REROLL_COST_VOUCHER_KEYS:
            from games.balatro.env.reroll_voucher_redemption import reroll_voucher_redemption_is_exact
            return reroll_voucher_redemption_is_exact(run, slot)
        if key in EXACT_INTEREST_CAP_VOUCHER_KEYS:
            from games.balatro.env.interest_cap_voucher_redemption import interest_cap_voucher_redemption_is_exact
            return interest_cap_voucher_redemption_is_exact(run, slot)
        if key in EXACT_SHOP_SIZE_VOUCHER_KEYS:
            from games.balatro.env.shop_size_voucher_redemption import shop_size_voucher_redemption_is_exact
            return shop_size_voucher_redemption_is_exact(run, slot)
        if key not in (_EXACT_RESOURCE_VOUCHER_KEYS | EXACT_EDITION_RATE_VOUCHER_KEYS):
            return False
        if key in state.vouchers:
            return False
        if key == "v_glow_up" and "v_hone" not in state.vouchers:
            return False
        if key in _HAND_ALLOWANCE_VOUCHER_KEYS and not state.round_reset_hands_observed:
            return False
        if key in _DISCARD_ALLOWANCE_VOUCHER_KEYS and not state.round_reset_discards_observed:
            return False
        return True

    @staticmethod
    def _apply_voucher_redemption_effects(state: BalatroState, key: str) -> None:
        if key == "v_crystal_ball":
            state.consumable_slots += 1
        elif key in _HAND_ALLOWANCE_VOUCHER_KEYS:
            state.round_reset_hands += 1
            state.hands_remaining += 1
        elif key in _DISCARD_ALLOWANCE_VOUCHER_KEYS:
            state.round_reset_discards += 1
            state.discards_remaining += 1
        elif key == "v_antimatter":
            state.joker_slots += 1
        elif key in {"v_paint_brush", "v_palette"}:
            state.hand_size += 1
        elif key == "v_hone":
            state.joker_generation_edition_rate = 2.0
        elif key == "v_glow_up":
            state.joker_generation_edition_rate = 4.0
        else:
            raise HeadlessTransitionError("unsupported Voucher redemption effect")

    @staticmethod
    def _voucher_key(item: Any) -> str:
        key = getattr(item, "center_key", None)
        if not isinstance(key, str) or not key:
            raise HeadlessTransitionError("shop Voucher has no exact center key")
        return key

    @classmethod
    def _is_affordable(cls, state: BalatroState, item: Any) -> bool:
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
