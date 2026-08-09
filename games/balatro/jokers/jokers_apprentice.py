from games.balatro.joker import Joker, JokerContext


class JokersApprentice(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        context.data["wild_card"] = True

        return context