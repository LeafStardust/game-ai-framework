import random

from dataclasses import dataclass

from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.joker import JokerContext
from games.balatro.events import BalatroEvent, BalatroEventType


@dataclass
class HandScore:

    chips: int
    mult: int
    x_mult: float = 1.0

    @property
    def total(self) -> int:
        return int(
            self.chips
            * self.mult
            * self.x_mult
        )


class BalatroScorer:

    SCORES = {
        PokerHand.HIGH_CARD: HandScore(5, 1),
        PokerHand.PAIR: HandScore(10, 2),
        PokerHand.TWO_PAIR: HandScore(20, 2),
        PokerHand.THREE_OF_A_KIND: HandScore(30, 3),
        PokerHand.STRAIGHT: HandScore(30, 4),
        PokerHand.FLUSH: HandScore(35, 4),
        PokerHand.FULL_HOUSE: HandScore(40, 4),
        PokerHand.FOUR_OF_A_KIND: HandScore(60, 7),
        PokerHand.STRAIGHT_FLUSH: HandScore(100, 8),
        PokerHand.FIVE_OF_A_KIND: HandScore(120, 12),
        PokerHand.FLUSH_HOUSE: HandScore(140, 14),
        PokerHand.FLUSH_FIVE: HandScore(160, 16),
    }

    RANK_CHIPS = {
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
        "10": 10,
        "J": 10,
        "Q": 10,
        "K": 10,
        "A": 11,
    }

    ON_SCORED_JOKER_CLASS_NAMES = frozenset(
        {
            "AncientJoker",
            "ArrowheadJoker",
            "BloodstoneJoker",
            "EvenStevenJoker",
            "FibonacciJoker",
            "GluttonousJoker",
            "GreedyJoker",
            "LustyJoker",
            "OddToddJoker",
            "OnyxAgateJoker",
            "PhotographJoker",
            "ScaryFaceJoker",
            "ScholarJoker",
            "SmileyFaceJoker",
            "TheIdolJoker",
            "TribouletJoker",
            "WalkieTalkieJoker",
            "WeeJoker",
            "WrathfulJoker",
        }
    )

    ALSO_INDEPENDENT_JOKER_CLASS_NAMES = frozenset(
        {
            "WeeJoker",
        }
    )

    ON_HELD_JOKER_CLASS_NAMES = frozenset(
        {
            "BaronJoker",
            "RaisedFistJoker",
            "ShootTheMoonJoker",
        }
    )

    def is_card_debuffed(self, card) -> bool:
        """Return whether Balatro currently disables this card's effects.

        Live observation exposes the public per-card ``debuff`` flag. Debuffed
        cards retain rank/suit for poker-hand classification, but their chips,
        enhancement/edition effects and held-card effects do not contribute.
        """
        return bool(getattr(card, "debuffed", False))

    @staticmethod
    def _played_card_trigger_count(card, extra_retriggers: int = 0) -> int:
        """Return how many times one scored card resolves its scoring effects."""
        branch_retriggers = max(
            0,
            int(getattr(card, "_projection_extra_retriggers", 0) or 0),
        )
        return (
            1
            + max(0, int(extra_retriggers))
            + branch_retriggers
            + (1 if getattr(card, "seal", None) == "Red" else 0)
        )

    @staticmethod
    def _held_card_trigger_count(card, extra_retriggers: int = 0) -> int:
        """Return held-in-hand activations for one public card."""
        return (
            1
            + max(0, int(extra_retriggers))
            + (1 if getattr(card, "seal", None) == "Red" else 0)
        )

    @staticmethod
    def _fold_x_mult(score: HandScore) -> None:
        """Commit XMult before a later additive Mult activation can resolve."""
        factor = float(score.x_mult)
        if factor != 1.0:
            score.mult *= factor
            score.x_mult = 1.0

    def _apply_card_modifiers(
        self,
        score: HandScore,
        cards,
        *,
        resolve_random_effects: bool = True,
        extra_retriggers: int = 0,
    ) -> None:

        for card in cards:

            if self.is_card_debuffed(card):
                continue

            for _ in range(
                self._played_card_trigger_count(card, extra_retriggers)
            ):
                self._apply_single_card_modifier(
                    score,
                    card,
                    resolve_random_effects=resolve_random_effects,
                )

    def _apply_single_card_modifier(
        self,
        score: HandScore,
        card,
        *,
        resolve_random_effects: bool = True,
    ) -> None:

        if card.enhancement == "Bonus":
            score.chips += 30

        elif card.enhancement == "Mult":
            score.mult += 4

        elif card.enhancement == "Glass":
            score.x_mult *= 2
            self._fold_x_mult(score)

        elif card.enhancement == "Stone":
            score.chips += 50

        elif (
            resolve_random_effects
            and card.enhancement == "Lucky"
            and random.random() < 0.2
        ):
            score.mult += 20

        if card.edition == "Foil":
            score.chips += 50

        elif card.edition == "Holographic":
            score.mult += 10

        elif card.edition == "Polychrome":
            score.x_mult *= 1.5
            self._fold_x_mult(score)

    @staticmethod
    def _apply_joker_pre_effect_edition(
        score: HandScore,
        joker,
    ) -> None:
        """Resolve Foil/Holographic before one Joker's independent effect."""
        edition = str(getattr(joker, "edition", "") or "").upper()
        if edition == "FOIL":
            score.chips += 50
        elif edition in {"HOLO", "HOLOGRAPHIC"}:
            score.mult += 10

    @staticmethod
    def _apply_joker_polychrome(
        score: HandScore,
        joker,
    ) -> None:
        """Resolve Polychrome after independent and on-other-Joker effects."""
        edition = str(getattr(joker, "edition", "") or "").upper()
        if edition == "POLYCHROME":
            score.x_mult *= 1.5

    @staticmethod
    def _joker_is_uncommon(joker) -> bool:
        return str(getattr(joker, "rarity", "") or "").upper() == "UNCOMMON"

    def _apply_baseball_card_triggers(
        self,
        context: JokerContext,
        baseball_cards,
        other_joker,
    ) -> JokerContext:
        if not baseball_cards or not self._joker_is_uncommon(other_joker):
            return context

        other_context = JokerContext(
            state=context.state,
            score=context.score,
            poker_hand=context.poker_hand,
            cards=context.cards,
            held_cards=context.held_cards,
            trigger="OTHER_JOKER",
            event=context.event,
            data={**context.data, "other_joker": other_joker},
        )
        for baseball_card in baseball_cards:
            other_context = baseball_card.apply(other_context)
            self._fold_x_mult(other_context.score)
        context.score = other_context.score
        return context

    def _apply_scoring_card_phase(
        self,
        score: HandScore,
        hand: PokerHand,
        state,
        played_cards,
        scoring_cards,
        *,
        extra_retriggers: int = 0,
        resolve_random_effects: bool = True,
        context_data: dict | None = None,
    ) -> None:
        """Resolve scoring cards left-to-right, including on-scored Jokers."""
        active_scoring_cards = [
            card
            for card in scoring_cards
            if not self.is_card_debuffed(card)
        ]
        first_scoring_face_card = next(
            (
                card
                for card in active_scoring_cards
                if str(getattr(card, "rank", "")) in {"J", "Q", "K"}
            ),
            None,
        )
        on_scored_jokers = []
        if state is not None:
            on_scored_jokers = [
                joker
                for joker in getattr(state, "jokers", [])
                if type(joker).__name__ in self.ON_SCORED_JOKER_CLASS_NAMES
            ]

        for card in active_scoring_cards:
            trigger_count = self._played_card_trigger_count(
                card,
                extra_retriggers,
            )
            for _ in range(trigger_count):
                score.chips += self.card_chip_value(card)
                self._apply_single_card_modifier(
                    score,
                    card,
                    resolve_random_effects=resolve_random_effects,
                )

                if not on_scored_jokers:
                    continue

                card_data = dict(context_data or {})
                card_data.update(
                    {
                        "scoring_cards": [card],
                        "current_scoring_card": card,
                        "first_scoring_face_card": first_scoring_face_card,
                        "resolve_random_effects": resolve_random_effects,
                    }
                )
                context = JokerContext(
                    state=state,
                    score=score,
                    poker_hand=hand,
                    cards=list(played_cards or []),
                    held_cards=[],
                    trigger="CARD_SCORED",
                    data=card_data,
                )
                for joker in on_scored_jokers:
                    context = joker.apply(context)
                    self._fold_x_mult(context.score)

    def _apply_held_phase(
        self,
        score: HandScore,
        cards,
        state,
        *,
        extra_retriggers: int = 0,
    ) -> None:
        """Resolve public held-card scoring effects in Balatro activation order."""
        active_cards = [
            card
            for card in list(cards or [])
            if not self.is_card_debuffed(card)
        ]
        ranked_cards = [
            card
            for card in active_cards
            if getattr(card, "enhancement", None) != "Stone"
            and str(getattr(card, "rank", "")) in self.RANK_CHIPS
        ]
        lowest = min(
            ranked_cards,
            key=lambda card: self.RANK_CHIPS[str(card.rank)],
            default=None,
        )
        held_jokers = [
            joker
            for joker in getattr(state, "jokers", [])
            if type(joker).__name__ in self.ON_HELD_JOKER_CLASS_NAMES
        ]

        for card in active_cards:
            trigger_count = self._held_card_trigger_count(
                card,
                extra_retriggers,
            )
            for _ in range(trigger_count):
                if getattr(card, "enhancement", None) == "Steel":
                    score.x_mult *= 1.5
                    self._fold_x_mult(score)

                if not held_jokers:
                    continue

                context = JokerContext(
                    state=state,
                    score=score,
                    cards=[],
                    held_cards=active_cards,
                    trigger="HELD_CARD",
                    data={
                        "held_card": card,
                        "lowest_held_card": lowest,
                    },
                )
                for joker in held_jokers:
                    context = joker.apply(context)
                    self._fold_x_mult(context.score)

    def score(
        self,
        hand: PokerHand,
        state=None,
        cards=None,
        *,
        include_card_chips: bool = False,
        resolve_random_effects: bool = True,
        joker_data: dict | None = None,
    ) -> HandScore:

        base_score = self.SCORES[hand]
        hand_level = 1

        if state is not None:
            hand_levels = getattr(state, "hand_levels", {})
            hand_level = hand_levels.get(
                hand.value,
                hand_levels.get(hand, 1),
            )

        score = HandScore(
            base_score.chips,
            base_score.mult,
            base_score.x_mult,
        )

        if hand_level > 1:
            from games.balatro.planets import PLANET_CARDS

            planet = next(
                (
                    planet
                    for planet in PLANET_CARDS.values()
                    if planet.hand_type == hand.value
                ),
                None,
            )
            if planet is not None:
                score.chips += planet.chips * (hand_level - 1)
                score.mult += planet.mult * (hand_level - 1)

        played_cards = list(cards or [])
        context_data = dict(joker_data or {})
        rules = context_data.get("hand_rules")
        if rules is None:
            rules = hand_rules_for_state(state)
            context_data["hand_rules"] = rules
        scoring_cards = self.scoring_cards(
            hand,
            played_cards,
            rules=rules,
        )
        played_card_retriggers = max(
            0,
            int(context_data.get("retrigger_played_cards", 0) or 0),
        )
        held_card_retriggers = max(
            0,
            int(context_data.get("retrigger_held_abilities", 0) or 0),
        )

        if include_card_chips:
            self._apply_scoring_card_phase(
                score,
                hand,
                state,
                played_cards,
                scoring_cards,
                extra_retriggers=played_card_retriggers,
                resolve_random_effects=resolve_random_effects,
                context_data=context_data,
            )
        else:
            self._apply_card_modifiers(
                score,
                played_cards,
                resolve_random_effects=resolve_random_effects,
            )

        if state is not None:
            held_cards = getattr(state, "hand", [])
            if include_card_chips and played_cards:
                played_identity = {id(card) for card in played_cards}
                held_cards = [
                    card
                    for card in held_cards
                    if id(card) not in played_identity
                ]

            self._fold_x_mult(score)
            self._apply_held_phase(
                score,
                held_cards,
                state,
                extra_retriggers=held_card_retriggers,
            )

            context_data["scoring_cards"] = [
                card
                for card in scoring_cards
                if not self.is_card_debuffed(card)
            ]
            context_data.setdefault(
                "most_played_hands",
                self.most_played_hands(state),
            )

            context = JokerContext(
                state=state,
                score=score,
                poker_hand=hand,
                cards=played_cards,
                held_cards=held_cards,
                trigger="HAND_SCORED",
                event=BalatroEvent(
                    BalatroEventType.HAND_SCORED,
                    played_cards,
                ),
                data=context_data,
            )

            baseball_cards = [
                joker
                for joker in state.jokers
                if type(joker).__name__ == "BaseballCardJoker"
            ]
            for joker in state.jokers:
                class_name = type(joker).__name__
                self._apply_joker_pre_effect_edition(context.score, joker)
                if (
                    not include_card_chips
                    or class_name not in self.ON_SCORED_JOKER_CLASS_NAMES
                    or class_name in self.ALSO_INDEPENDENT_JOKER_CLASS_NAMES
                ):
                    context = joker.apply(context)
                self._fold_x_mult(context.score)
                context = self._apply_baseball_card_triggers(
                    context,
                    baseball_cards,
                    joker,
                )
                self._apply_joker_polychrome(context.score, joker)
                self._fold_x_mult(context.score)

            score = context.score

        return score

    @classmethod
    def most_played_hands(cls, state) -> set[PokerHand]:
        counts = getattr(state, "hand_play_counts", {})
        by_hand = {
            hand: int(counts.get(hand.value, counts.get(hand, 0)) or 0)
            for hand in PokerHand
        }
        maximum = max(by_hand.values(), default=0)
        if maximum <= 0:
            return set()
        return {
            hand
            for hand, count in by_hand.items()
            if count == maximum
        }

    @classmethod
    def card_chip_value(cls, card) -> int:
        permanent_bonus = int(getattr(card, "permanent_bonus", 0) or 0)
        if getattr(card, "enhancement", None) == "Stone":
            return permanent_bonus
        return (
            cls.RANK_CHIPS.get(str(getattr(card, "rank", "")), 0)
            + permanent_bonus
        )

    @classmethod
    def scoring_cards(
        cls,
        hand: PokerHand,
        cards,
        rules: dict | None = None,
    ) -> list:
        """Return Joker-aware scoring-card membership for one recognized hand."""
        return HandEvaluator().scoring_cards(
            hand,
            list(cards or []),
            rules=rules,
        )
