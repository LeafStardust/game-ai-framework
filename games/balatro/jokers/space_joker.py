import random

from games.balatro.joker import Joker, JokerContext


class SpaceJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:

        if context.poker_hand is None:
            return context

        if random.random() < 0.25:
            context.data.setdefault(
                "level_ups",
                []
            ).append(
                context.poker_hand
            )

        return context