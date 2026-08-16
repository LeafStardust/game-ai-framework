from games.balatro.joker import Joker, JokerContext


class DuskJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_PLAYED":
            return context
        if not context.data.get("final_hand"):
            return context

        context.data["retrigger_played_cards"] = (
            int(context.data.get("retrigger_played_cards", 0) or 0) + 1
        )

        return context
