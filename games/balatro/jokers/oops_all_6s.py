from games.balatro.joker import Joker, JokerContext


class OopsAll6sJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "PROBABILITY_CHECK":
            return context

        if "probability" not in context.data:
            return context

        context.data["probability"] *= 2

        return context