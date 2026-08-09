from games.balatro.joker import Joker, JokerContext


class ChaosTheClownJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "SHOP_ENTERED":
            return context

        context.data["free_rerolls"] = (
            context.data.get("free_rerolls", 0) + 1
        )

        return context