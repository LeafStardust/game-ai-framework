import random

from games.balatro.joker import Joker, JokerContext


class CavendishJoker(Joker):

    def __init__(self):
        self.active = True

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None or not self.active:
            return context

        context.score.x_mult *= 3

        if random.random() < 0.001:
            self.active = False
            context.data["remove_joker"] = self

        return context