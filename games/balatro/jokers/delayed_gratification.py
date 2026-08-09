from games.balatro.joker import Joker, JokerContext


class DelayedGratificationJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "ROUND_ENDED":
            return context

        if context.data.get("discards_remaining", 0) == 0:
            return context

        context.data["delayed_gratification_money"] = (
            context.data.get("delayed_gratification_money", 0)
            + context.data["discards_remaining"] * 2
        )

        return context