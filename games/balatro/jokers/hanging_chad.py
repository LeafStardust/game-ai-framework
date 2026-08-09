from games.balatro.joker import Joker, JokerContext


class HangingChadJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if not context.cards:
            return context

        context.data["retrigger_first_card"] = (
            context.data.get("retrigger_first_card", 0) + 2
        )

        return context