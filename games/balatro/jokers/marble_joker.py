from games.balatro.card import BalatroCard
from games.balatro.joker import Joker, JokerContext


class MarbleJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "ROUND_STARTED":
            return context

        context.data.setdefault(
            "created_cards",
            []
        ).append(
            BalatroCard(
                "Stone",
                "None",
                enhancement="Stone"
            )
        )

        return context