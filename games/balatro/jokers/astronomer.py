from games.balatro.joker import Joker, JokerContext
from games.balatro.mechanics import PLANET_GENERATION


class AstronomerJoker(Joker):
    mechanics = frozenset({PLANET_GENERATION})

    def apply(self, context: JokerContext) -> JokerContext:
        context.data["planet_cards_free"] = True
        context.data["celestial_packs_free"] = True

        return context
