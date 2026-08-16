from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from games.balatro.deck_rules import starting_deck_size_for_name
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.joker import JokerContext
from games.balatro.live.copy_projection import (
    COPY_JOKER_CLASS_NAMES,
    INDEPENDENT_COPY_TARGET_CLASS_NAMES,
    project_independent_copy_jokers,
    resolve_copy_target,
)
from games.balatro.scoring import BalatroScorer, HandScore


@dataclass(frozen=True)
class JokerScoreProjection:
    """One side-effect-free Joker-aware scoring transition."""

    score: HandScore
    state_after_scoring: object | None
    cards_after_copy: tuple
    unsupported_jokers: tuple[str, ...] = ()
    played_card_retriggers: int = 0

    @property
    def complete(self) -> bool:
        return not self.unsupported_jokers


class LiveJokerScoreProjector:
    """Apply explicitly validated live Jokers on an isolated branch state."""

    SUPPORTED_CLASS_NAMES = frozenset(
        {
            "AbstractJoker",
            "AcrobatJoker",
            "AncientJoker",
            "ArrowheadJoker",
            "AstronomerJoker",
            "BannerJoker",
            "BaronJoker",
            "BaseballCardJoker",
            "BlackboardJoker",
            "BloodstoneJoker",
            "BlueJoker",
            "BlueprintJoker",
            "BootstrapsJoker",
            "BrainstormJoker",
            "BullJoker",
            "BurglarJoker",
            "CampfireJoker",
            "CanioJoker",
            "CardSharpJoker",
            "CastleJoker",
            "CavendishJoker",
            "ChaosTheClownJoker",
            "CleverJoker",
            "ConstellationJoker",
            "CraftyJoker",
            "CrazyJoker",
            "CreditCardJoker",
            "DaggerJoker",
            "DeviousJoker",
            "DietColaJoker",
            "DriversLicenseJoker",
            "DrollJoker",
            "DrunkardJoker",
            "DuskJoker",
            "EggJoker",
            "ErosionJoker",
            "EvenStevenJoker",
            "FibonacciJoker",
            "FlashCardJoker",
            "FlatMultJoker",
            "FlowerPotJoker",
            "FortuneTellerJoker",
            "FourFingersJoker",
            "GluttonousJoker",
            "GoldenTicketJoker",
            "GreenJoker",
            "GreedyJoker",
            "GrosMichelJoker",
            "HackJoker",
            "HalfJoker",
            "HangingChadJoker",
            "HikerJoker",
            "HitTheRoadJoker",
            "HologramJoker",
            "IceCreamJoker",
            "InvisibleJoker",
            "JokerStencil",
            "JollyJoker",
            "JugglerJoker",
            "LoyaltyCardJoker",
            "LuckyCatJoker",
            "LustyJoker",
            "MadJoker",
            "MadnessJoker",
            "MerryAndyJoker",
            "MimeJoker",
            "MysticSummitJoker",
            "ObeliskJoker",
            "OddToddJoker",
            "OnyxAgateJoker",
            "OopsAll6sJoker",
            "PareidoliaJoker",
            "PerkeoJoker",
            "PhotographJoker",
            "PopcornJoker",
            "RaisedFistJoker",
            "RamenJoker",
            "RedCardJoker",
            "RideTheBusJoker",
            "RoughGemJoker",
            "RunnerJoker",
            "ScaryFaceJoker",
            "ScholarJoker",
            "SeeingDoubleJoker",
            "SeltzerJoker",
            "ShootTheMoonJoker",
            "ShortcutJoker",
            "ShowmanJoker",
            "SlyJoker",
            "SmearedJoker",
            "SmileyFaceJoker",
            "SockAndBuskinJoker",
            "SpaceJoker",
            "SpareTrousersJoker",
            "SplashJoker",
            "SquareJoker",
            "SteelJoker",
            "StoneJoker",
            "StuntmanJoker",
            "SupernovaJoker",
            "SwashbucklerJoker",
            "TheDuoJoker",
            "TheFamilyJoker",
            "TheIdolJoker",
            "TheOrderJoker",
            "TheTribeJoker",
            "TheTrioJoker",
            "ThrowbackJoker",
            "TribouletJoker",
            "TroubadourJoker",
            "TurtleBeanJoker",
            "VampireJoker",
            "WalkieTalkieJoker",
            "WeeJoker",
            "WilyJoker",
            "WrathfulJoker",
            "YorickJoker",
            "ZanyJoker",
        }
    )

    DEFERRED_HYDRATED_CLASS_NAMES = frozenset()
    DEFERRED_REASONS_BY_CLASS = {}

    OWNED_DECK_REQUIRED_CLASS_NAMES = frozenset(
        {
            "DriversLicenseJoker",
            "ErosionJoker",
            "SteelJoker",
            "StoneJoker",
        }
    )

    VALID_JOKER_RARITIES = frozenset(
        {"COMMON", "UNCOMMON", "RARE", "LEGENDARY"}
    )

    HAND_PLAYED_CLASS_NAMES = frozenset(
        {
            "DuskJoker",
            "HackJoker",
            "HangingChadJoker",
            "LoyaltyCardJoker",
            "MimeJoker",
            "SockAndBuskinJoker",
            "VampireJoker",
        }
    )

    SCORING_ECONOMY_CLASS_NAMES = frozenset(
        {
            "GoldenTicketJoker",
            "RoughGemJoker",
        }
    )

    CARD_MUTATING_CLASS_NAMES = frozenset(
        {
            "HackJoker",
            "HangingChadJoker",
            "HikerJoker",
            "SockAndBuskinJoker",
            "VampireJoker",
        }
    )

    def __init__(self, scorer: BalatroScorer | None = None):
        self.scorer = scorer or BalatroScorer()

    @classmethod
    def supports(cls, joker) -> bool:
        return type(joker).__name__ in cls.SUPPORTED_CLASS_NAMES

    @classmethod
    def supports_in_state(cls, joker, state) -> bool:
        if not cls.supports(joker):
            return False
        class_name = type(joker).__name__
        if class_name in COPY_JOKER_CLASS_NAMES:
            target, resolvable = resolve_copy_target(joker, state)
            if not resolvable:
                return False
            if target is None:
                return True
            if type(target).__name__ not in INDEPENDENT_COPY_TARGET_CLASS_NAMES:
                return False
            if not cls.supports_in_state(target, state):
                return False
        if (
            class_name in cls.OWNED_DECK_REQUIRED_CLASS_NAMES
            and getattr(state, "owned_deck", None) is None
        ):
            return False
        if (
            class_name == "ErosionJoker"
            and starting_deck_size_for_name(
                getattr(state, "deck_name", None)
            ) is None
        ):
            return False
        if (
            class_name == "BaseballCardJoker"
            and not cls._has_complete_baseball_rarity_metadata(state)
        ):
            return False
        return True

    @classmethod
    def _has_complete_baseball_rarity_metadata(cls, state) -> bool:
        for candidate in getattr(state, "jokers", []):
            if type(candidate).__name__ == "BaseballCardJoker":
                continue
            rarity = str(getattr(candidate, "rarity", "") or "").upper()
            if rarity not in cls.VALID_JOKER_RARITIES:
                return False
        return True

    @classmethod
    def deferred_reason(cls, class_name: str) -> str | None:
        if class_name not in cls.DEFERRED_HYDRATED_CLASS_NAMES:
            return None
        return cls.DEFERRED_REASONS_BY_CLASS.get(
            class_name,
            "requires explicit HAND_SCORED/event-transition validation",
        )

    def unsupported_jokers(self, state) -> tuple[str, ...]:
        if state is None:
            return ()
        return tuple(
            self._joker_name(joker)
            for joker in getattr(state, "jokers", [])
            if not self.supports_in_state(joker, state)
        )

    def score(
        self,
        hand,
        state,
        cards,
        *,
        include_card_chips: bool = True,
        resolve_random_effects: bool = False,
    ) -> JokerScoreProjection:
        if state is None:
            score = self.scorer.score(
                hand,
                None,
                cards=list(cards or []),
                include_card_chips=include_card_chips,
                resolve_random_effects=resolve_random_effects,
            )
            return JokerScoreProjection(
                score=score,
                state_after_scoring=None,
                cards_after_copy=tuple(cards or ()),
            )

        safe_state = state.copy()
        safe_state.jokers = deepcopy(list(getattr(state, "jokers", [])))

        all_jokers = list(getattr(safe_state, "jokers", []))
        supported = [
            joker
            for joker in all_jokers
            if self.supports_in_state(joker, safe_state)
        ]
        unsupported = tuple(
            self._joker_name(joker)
            for joker in all_jokers
            if not self.supports_in_state(joker, safe_state)
        )

        if self._requires_card_isolation(supported):
            safe_cards = self._isolate_branch_cards(state, safe_state, cards)
        else:
            safe_cards = list(cards or [])

        projected_jokers = project_independent_copy_jokers(
            supported,
            safe_state,
        )
        safe_state.jokers = projected_jokers
        hand_rules = hand_rules_for_state(safe_state)
        joker_data = self._prepare_hand_play(
            hand,
            safe_state,
            safe_cards,
            projected_jokers,
            hand_rules=hand_rules,
        )
        joker_data["hand_rules"] = hand_rules
        joker_data["resolve_random_effects"] = bool(resolve_random_effects)

        played_card_retriggers = self._seltzer_retriggers(supported)
        if played_card_retriggers:
            joker_data["retrigger_played_cards"] = (
                int(joker_data.get("retrigger_played_cards", 0) or 0)
                + played_card_retriggers
            )

        self._apply_per_card_retriggers(joker_data, safe_cards)
        joker_data["scoring_cards"] = self._expanded_scoring_cards(
            hand,
            safe_cards,
            joker_data,
        )
        self._apply_scoring_economy(
            safe_state,
            joker_data["scoring_cards"],
            projected_jokers,
            hand_rules=hand_rules,
        )

        score = self.scorer.score(
            hand,
            safe_state,
            cards=safe_cards,
            include_card_chips=include_card_chips,
            resolve_random_effects=resolve_random_effects,
            joker_data=joker_data,
        )
        self._consume_seltzer_hand(supported)
        self._increment_hand_play_count(safe_state, hand)
        safe_state.jokers = all_jokers

        return JokerScoreProjection(
            score=score,
            state_after_scoring=safe_state,
            cards_after_copy=tuple(safe_cards),
            unsupported_jokers=unsupported,
            played_card_retriggers=played_card_retriggers,
        )

    def _prepare_hand_play(
        self,
        hand,
        state,
        cards,
        jokers,
        *,
        hand_rules: dict,
    ) -> dict:
        active = [
            joker
            for joker in jokers
            if type(joker).__name__ in self.HAND_PLAYED_CLASS_NAMES
        ]
        if not active:
            return {}

        scoring_cards = [
            card
            for card in self.scorer.scoring_cards(
                hand,
                cards,
                rules=hand_rules,
            )
            if not self.scorer.is_card_debuffed(card)
        ]
        context = JokerContext(
            state=state,
            poker_hand=hand,
            cards=list(cards or []),
            trigger="HAND_PLAYED",
            data={
                "scoring_cards": scoring_cards,
                "final_hand": int(getattr(state, "hands_remaining", 0) or 0) <= 1,
                "hand_rules": hand_rules,
            },
        )
        for joker in active:
            context = joker.apply(context)
        return context.data

    @staticmethod
    def _apply_per_card_retriggers(joker_data: dict, cards) -> None:
        by_card = joker_data.get("retrigger_by_card_id", {})
        if not isinstance(by_card, dict) or not by_card:
            return
        for card in cards:
            extra = max(0, int(by_card.get(id(card), 0) or 0))
            if extra:
                setattr(card, "_projection_extra_retriggers", extra)

    def _expanded_scoring_cards(self, hand, cards, joker_data: dict) -> list:
        global_retriggers = max(
            0,
            int(joker_data.get("retrigger_played_cards", 0) or 0),
        )
        rules = joker_data.get("hand_rules", {})
        expanded = []
        for card in self.scorer.scoring_cards(hand, cards, rules=rules):
            if self.scorer.is_card_debuffed(card):
                continue
            expanded.extend(
                [card]
                * self.scorer._played_card_trigger_count(
                    card,
                    global_retriggers,
                )
            )
        return expanded

    def _apply_scoring_economy(
        self,
        state,
        scoring_cards,
        jokers,
        *,
        hand_rules: dict,
    ) -> None:
        active = [
            joker
            for joker in jokers
            if type(joker).__name__ in self.SCORING_ECONOMY_CLASS_NAMES
        ]
        if not active:
            return

        for card in scoring_cards:
            context = JokerContext(
                state=state,
                cards=[card],
                trigger="CARD_SCORED",
                data={
                    "current_scoring_card": card,
                    "hand_rules": hand_rules,
                },
            )
            for joker in active:
                context = joker.apply(context)

    @staticmethod
    def _seltzer_retriggers(jokers) -> int:
        return sum(
            1
            for joker in jokers
            if type(joker).__name__ == "SeltzerJoker"
            and int(getattr(joker, "rounds_remaining", 0) or 0) > 0
        )

    @staticmethod
    def _consume_seltzer_hand(jokers) -> None:
        for joker in jokers:
            if type(joker).__name__ != "SeltzerJoker":
                continue
            remaining = int(getattr(joker, "rounds_remaining", 0) or 0)
            if remaining > 0:
                joker.rounds_remaining = remaining - 1

    @classmethod
    def _requires_card_isolation(cls, jokers) -> bool:
        return any(
            type(joker).__name__ in cls.CARD_MUTATING_CLASS_NAMES
            for joker in jokers
        )

    @staticmethod
    def _isolate_branch_cards(state, safe_state, cards) -> list:
        copies: dict[int, object] = {}

        def clone(card):
            key = id(card)
            if key not in copies:
                copies[key] = deepcopy(card)
            return copies[key]

        safe_state.hand = [clone(card) for card in getattr(state, "hand", [])]
        safe_state.deck = [clone(card) for card in getattr(state, "deck", [])]
        return [clone(card) for card in list(cards or [])]

    @staticmethod
    def _increment_hand_play_count(state, hand) -> None:
        for attribute in ("hand_play_counts", "round_hand_play_counts"):
            counts = getattr(state, attribute, None)
            if not isinstance(counts, dict):
                continue

            current = int(counts.get(hand.value, counts.get(hand, 0)) or 0)
            updated = current + 1
            counts[hand.value] = updated
            if hand in counts:
                counts[hand] = updated

    @staticmethod
    def _joker_name(joker) -> str:
        label = getattr(joker, "label", None)
        if isinstance(label, str) and label:
            return label
        name = type(joker).__name__
        return name.removesuffix("Joker").replace("_", " ")
