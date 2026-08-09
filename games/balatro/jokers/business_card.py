import random

from games.balatro.joker import Joker, JokerContext


class BusinessCardJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context

        money = sum(
            2
            for card in context.cards
            if card.rank in {"J", "Q", "K"}
            and random.random() < 0.5
        )

        context.data["money"] = (
            context.data.get("money", 0) + money
        )

        return context