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

        # Category marker only; live projection resolves random identity separately.
        context.data.setdefault("created_consumables", []).append("Tarot")
        return context
