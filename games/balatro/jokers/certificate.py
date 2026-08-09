import random

from games.balatro.card import BalatroCard
from games.balatro.joker import Joker, JokerContext


class CertificateJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        rank = random.choice(
            ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        )
        suit = random.choice(
            ["Hearts", "Diamonds", "Clubs", "Spades"]
        )

        card = BalatroCard(rank, suit)

        context.data.setdefault(
            "created_cards",
            []
        ).append(card)

        if card.seal is not None:
            context.score.mult += 3

        return context