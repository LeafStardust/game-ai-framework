from games.balatro.joker import Joker, JokerContext


class DuskJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "LAST_HAND":
            return context

        context.data["retrigger_played_cards"] = (
            context.data.get("retrigger_played_cards", 0) + 1
        )

        return context