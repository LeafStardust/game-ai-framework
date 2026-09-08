import random

from games.balatro.joker import Joker, JokerContext
from games.balatro.mechanics import PROBABILISTIC_HAND_LEVELING


class SpaceJoker(Joker):
    mechanics = frozenset({PROBABILISTIC_HAND_LEVELING})

    def apply(self, context: JokerContext) -> JokerContext:

        if context.trigger != "HAND_SCORED" or context.poker_hand is None:
            return context

        # Live projection supplies explicit stochastic branches outside the scorer.
        # Never consume hidden RNG while evaluating a hypothetical hand.
        if context.data.get("resolve_random_effects") is False:
            return context

        if random.random() < 0.25:
            context.data.setdefault(
                "level_ups",
                []
            ).append(
                context.poker_hand
            )

        return context
