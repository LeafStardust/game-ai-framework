import random

from games.balatro.joker import Joker, JokerContext


class CartomancerJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "BLIND_SELECTED":
            return context

        tarot = random.choice([
            "The Fool",
            "The Magician",
            "The High Priestess",
            "The Empress",
            "The Emperor",
        ])

        context.data.setdefault(
            "created_consumables",
            []
        ).append(tarot)

        return context