import random

from collections import Counter
from dataclasses import dataclass

from games.balatro.hand import PokerHand
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

    def _apply_card_modifiers(
        self,
        score: HandScore,
        cards
    ) -> None:

        for card in cards:

            self._apply_single_card_modifier(
                score,
                card
            )

            if card.seal == "Red":
                self._apply_single_card_modifier(
                    score,
                    card
                )

    def _apply_single_card_modifier(
        self,
        score: HandScore,
        card
    ) -> None:

        if card.enhancement == "Bonus":
            score.chips += 30

        elif card.enhancement == "Mult":
            score.mult += 4

        elif card.enhancement == "Glass":
            score.x_mult *= 2

        elif card.enhancement == "Stone":
            score.chips += 50

        if card.edition == "Foil":
            score.chips += 50

        elif card.edition == "Holographic":
            score.mult += 10

        elif card.edition == "Polychrome":
            score.x_mult *= 1.5

        if card.enhancement == "Lucky":
            if random.random() < 0.2:
                score.mult += 20

    def _apply_held_modifiers(
        self,
        score: HandScore,
        cards
    ) -> None:

        for card in cards:

            if card.enhancement == "Steel":
                score.x_mult *= 1.5

    def score(
        self,
        hand: PokerHand,
        state=None,
        cards=None,
        *,
        include_card_chips: bool = False,
    ) -> HandScore:

        base_score = self.SCORES[hand]

        hand_level = 1

        if state is not None:

            hand_levels = getattr(
                state,
                "hand_levels",
                {}
            )

            hand_level = hand_levels.get(
                hand.value,
                1
            )

        score = HandScore(
            base_score.chips,
            base_score.mult,
            base_score.x_mult
        )

        if hand_level > 1:

            from games.balatro.planets import PLANET_CARDS

            planet = next(
                (
                    planet
                    for planet in PLANET_CARDS.values()
                    if planet.hand_type == hand.value
                ),
                None
            )

            if planet is not None:

                score.chips += (
                    planet.chips
                    * (hand_level - 1)
                )

                score.mult += (
                    planet.mult
                    * (hand_level - 1)
                )

        played_cards = cards or []
        modifier_cards = played_cards

        if include_card_chips:
            modifier_cards = self.scoring_cards(hand, played_cards)
            score.chips += sum(
                self.card_chip_value(card)
                for card in modifier_cards
            )

        self._apply_card_modifiers(
            score,
            modifier_cards
        )

        if state is not None:

            held_cards = getattr(
                state,
                "hand",
                []
            )
            if include_card_chips and played_cards:
                played_identity = {id(card) for card in played_cards}
                held_cards = [
                    card
                    for card in held_cards
                    if id(card) not in played_identity
                ]

            self._apply_held_modifiers(
                score,
                held_cards
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
                    played_cards
                )
            )

            for joker in state.jokers:
                context = joker.apply(context)

            score = context.score

        return score

    @classmethod
    def card_chip_value(cls, card) -> int:
        if getattr(card, "enhancement", None) == "Stone":
            return 0
        return cls.RANK_CHIPS.get(str(getattr(card, "rank", "")), 0)

    @classmethod
    def scoring_cards(cls, hand: PokerHand, cards) -> list:
        """Return ordinary cards that contribute chips for a standard poker hand.

        This is used by live decision estimates. It intentionally leaves Joker-
        specific scoring overrides such as Splash for a future Joker-aware layer.
        Stone cards are always included because their enhancement scores directly.
        """
        played = list(cards or [])
        if not played:
            return []

        stones = [
            card
            for card in played
            if getattr(card, "enhancement", None) == "Stone"
        ]
        regular = [card for card in played if card not in stones]
        if not regular:
            return stones

        counts = Counter(str(getattr(card, "rank", "")) for card in regular)

        if hand == PokerHand.HIGH_CARD:
            highest = max(
                regular,
                key=lambda card: cls.card_chip_value(card),
            )
            selected = [highest]

        elif hand == PokerHand.PAIR:
            pair_rank = next(
                (rank for rank, count in counts.items() if count >= 2),
                None,
            )
            selected = [
                card
                for card in regular
                if str(getattr(card, "rank", "")) == pair_rank
            ][:2]

        elif hand == PokerHand.TWO_PAIR:
            pair_ranks = {
                rank
                for rank, count in counts.items()
                if count >= 2
            }
            selected = [
                card
                for card in regular
                if str(getattr(card, "rank", "")) in pair_ranks
            ][:4]

        elif hand == PokerHand.THREE_OF_A_KIND:
            trip_rank = next(
                (rank for rank, count in counts.items() if count >= 3),
                None,
            )
            selected = [
                card
                for card in regular
                if str(getattr(card, "rank", "")) == trip_rank
            ][:3]

        elif hand == PokerHand.FOUR_OF_A_KIND:
            quad_rank = next(
                (rank for rank, count in counts.items() if count >= 4),
                None,
            )
            selected = [
                card
                for card in regular
                if str(getattr(card, "rank", "")) == quad_rank
            ][:4]

        else:
            selected = regular

        selected_ids = {id(card) for card in selected}
        selected.extend(card for card in stones if id(card) not in selected_ids)
        return selected
