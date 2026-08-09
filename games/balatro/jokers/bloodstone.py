import random

from games.balatro.joker import Joker, JokerContext


class BloodstoneJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:

        if context.score is None:
            return context

        for card in context.cards:
            if card.suit == "Hearts":
                if random.random() < 0.5:
                    context.score.x_mult *= 1.5

        return context