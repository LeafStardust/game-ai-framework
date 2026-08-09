from games.balatro.joker import Joker, JokerContext


class FourFingersJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        context.data["straight_flush_size"] = 4
        context.data["flush_size"] = 4
        context.data["straight_size"] = 4

        return context