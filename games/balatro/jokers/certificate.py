import random

from games.balatro.card import BalatroCard
from games.balatro.joker import Joker, JokerContext


class CertificateJoker(Joker):

    RANKS = [
        "2", "3", "4", "5", "6", "7", "8", "9",
        "10", "J", "Q", "K", "A"
    ]

    SUITS = [
        "Hearts",
        "Diamonds",
        "Clubs",
        "Spades",
    ]

    SEALS = [
        "Red",
        "Blue",
        "Gold",
        "Purple",
    ]

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "ROUND_STARTED":
            return context

        if context.data.get("hand_full", False):
            return context

        card = BalatroCard(
            random.choice(self.RANKS),
            random.choice(self.SUITS)
        )

        card.seal = random.choice(self.SEALS)

        context.data.setdefault(
            "created_cards",
            []
        ).append(card)

        return context