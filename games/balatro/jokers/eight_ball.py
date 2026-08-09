import random

from games.balatro.joker import Joker, JokerContext


class EightBallJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context

        eights = sum(
            card.rank == "8"
            for card in context.cards
        )

        if eights and random.random() < 0.25:
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