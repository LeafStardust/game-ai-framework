from games.balatro.joker import Joker, JokerContext


class BurglarJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "BLIND_SELECTED":
            return context

        context.data["hands_gained"] = (
            context.data.get("hands_gained", 0) + 3
        )
        context.data["discards_lost"] = (
            context.data.get("discards_lost", 0)
            + context.data.get("discards_remaining", 0)
        )

        return context