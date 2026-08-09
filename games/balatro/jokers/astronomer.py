from games.balatro.joker import Joker, JokerContext


class AstronomerJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        context.data["planet_cards_free"] = True
        context.data["celestial_packs_free"] = True

        return context