import random

from games.balatro.joker import Joker, JokerContext


class MadnessJoker(Joker):

    def __init__(self):
        self.x_mult = 1.0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger not in {
            "SMALL_BLIND_SELECTED",
            "BIG_BLIND_SELECTED",
        }:
            return context

        self.x_mult += 0.5

        jokers = [
            joker
            for joker in getattr(context.state, "jokers", [])
            if joker is not self
        ]

        if jokers:
            context.data["destroy_joker"] = random.choice(jokers)

        if context.score is not None:
            context.score.x_mult *= self.x_mult

        return context