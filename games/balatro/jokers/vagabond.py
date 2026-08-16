from games.balatro.joker import Joker, JokerContext


class VagabondJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context

        money = context.data.get(
            "money_at_hand_play",
            getattr(context.state, "money", 0),
        )
        if int(money or 0) > 4:
            return context

        context.data["create_tarot_count"] = (
            int(context.data.get("create_tarot_count", 0) or 0) + 1
        )
        return context
