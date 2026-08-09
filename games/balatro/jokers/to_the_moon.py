from games.balatro.joker import Joker, JokerContext


class ToTheMoonJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "INTEREST_CALCULATED":
            return context

        context.data["interest_bonus"] = (
            context.data.get("interest_bonus", 0) + 1
        )

        return context