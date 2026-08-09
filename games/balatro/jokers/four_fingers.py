from games.balatro.joker import Joker, JokerContext


class FourFingersJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.data.get("four_fingers"):
            return context

        context.data["four_fingers"] = True

        return context