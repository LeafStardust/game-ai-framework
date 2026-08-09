from games.balatro.joker import Joker, JokerContext


class ShowmanJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        context.data["allow_duplicates"] = True

        return context