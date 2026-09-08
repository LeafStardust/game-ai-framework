from games.balatro.joker import Joker, JokerContext


class GoldenJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger == "ROUND_ENDED":
            context.data["money"] = (
                context.data.get("money", 0) + 4
            )

        return context