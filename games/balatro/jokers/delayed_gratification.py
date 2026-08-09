from games.balatro.joker import Joker, JokerContext


class DelayedGratificationJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "ROUND_ENDED":
            return context

        discards_remaining = context.data.get("discards_remaining", 0)

        if discards_remaining <= 0:
            return context

        context.data["delayed_gratification_money"] = (
            context.data.get("delayed_gratification_money", 0)
            + discards_remaining * 2
        )

        return context