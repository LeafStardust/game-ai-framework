from games.balatro.joker import Joker, JokerContext


class CreditCardJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        context.data["max_debt"] = min(
            context.data.get("max_debt", 0),
            -20
        )

        return context