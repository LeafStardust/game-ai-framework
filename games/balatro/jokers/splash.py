from games.balatro.joker import Joker, JokerContext


class SplashJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:

        context.data["all_cards_score"] = True

        return context