import random

from games.balatro.joker import Joker, JokerContext


class MisprintJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:

        if context.score is not None:
            context.score.mult += random.randint(0, 23)

        return context