from games.balatro.joker import Joker, JokerContext


class DietColaJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "SOLD":
            return context

        if context.data.get("sold_joker") is not self:
            return context

        context.data["double_tag"] = True

        return context