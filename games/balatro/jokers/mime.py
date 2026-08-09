from games.balatro.joker import Joker, JokerContext


class MimeJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        context.data["retrigger_held_abilities"] = (
            context.data.get("retrigger_held_abilities", 0) + 1
        )

        return context