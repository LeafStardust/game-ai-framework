import random

from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext


class SeanceJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.poker_hand != PokerHand.STRAIGHT_FLUSH:
            return context

        spectral = random.choice([
            "Familiar",
            "Grim",
            "Incantation",
            "Talisman",
            "Aura",
        ])

        context.data.setdefault(
            "created_consumables",
            []
        ).append(spectral)

        return context