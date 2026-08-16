import random

from games.balatro.joker import Joker, JokerContext


class MisprintJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        projected_results = context.data.get("misprint_results")
        if projected_results is not None:
            try:
                bonus = int(next(projected_results))
            except StopIteration:
                bonus = 0
        elif bool(context.data.get("resolve_random_effects", True)):
            bonus = random.randint(0, 23)
        else:
            bonus = 0

        context.score.mult += max(0, min(23, bonus))

        return context
