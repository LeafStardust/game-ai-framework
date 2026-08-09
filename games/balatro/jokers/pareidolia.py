from games.balatro.joker import Joker, JokerContext


class PareidoliaJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        context.data["all_cards_are_face"] = True

        return context