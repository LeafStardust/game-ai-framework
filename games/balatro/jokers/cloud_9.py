from games.balatro.joker import Joker, JokerContext


class Cloud9Joker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "ROUND_ENDED":
            return context

        hand_size = len(
            getattr(context.state, "hand", [])
        )

        context.data["money"] = (
            context.data.get("money", 0)
            + hand_size
        )

        return context