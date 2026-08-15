import random

from games.balatro.joker import Joker, JokerContext


class AncientJoker(Joker):

    SUITS = (
        "Hearts",
        "Diamonds",
        "Clubs",
        "Spades",
    )

    def __init__(self):
        self.suit = None

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger == "ROUND_STARTED":
            self.suit = random.choice(self.SUITS)
            return context

        if context.score is None or self.suit is None:
            return context

        scoring_cards = context.data.get("scoring_cards", context.cards)
        matching_cards = sum(
            card.matches_suit(self.suit)
            for card in scoring_cards
        )

        context.score.x_mult *= 1.5 ** matching_cards

        return context
