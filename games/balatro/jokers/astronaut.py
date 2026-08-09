import random

from games.balatro.joker import Joker, JokerContext


class AstronautJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        if random.random() < 0.25:
            context.data["level_up_hand"] = context.poker_hand

        return context