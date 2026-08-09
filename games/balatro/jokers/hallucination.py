import random

from games.balatro.joker import Joker, JokerContext


class HallucinationJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "BOOSTER_OPENED":
            return context

        if random.random() >= 0.5:
            return context

        context.data.setdefault(
            "created_consumables",
            []
        ).append("Random Tarot")

        return context