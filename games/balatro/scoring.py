import random

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

    def _apply_card_modifiers(
        self,
        score: HandScore,
        cards
    ) -> None:

        for card in cards:

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

            if card.seal == "Red":
                pass

            elif card.seal == "Gold":
                pass

            elif card.enhancement == "Lucky":
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
        cards=None
    ) -> HandScore:

        base_score = self.SCORES[hand]

        score = HandScore(
            base_score.chips,
            base_score.mult,
            base_score.x_mult
        )

        played_cards = cards or []

        self._apply_card_modifiers(
            score,
            played_cards
        )

        if state is not None:

            held_cards = getattr(
                state,
                "hand",
                []
            )

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