import random

from games.balatro.joker import Joker, JokerContext


class VagabondJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        money = context.data.get(
            "money",
            getattr(context.state, "money", 0)
        )

        if money > 4:
            return context

        context.data.setdefault(
            "created_consumables",
            []
        ).append(
            random.choice([
                "The Fool",
                "The Magician",
                "The High Priestess",
                "The Empress",
                "The Emperor",
            ])
        )

        return context