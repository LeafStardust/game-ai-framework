from games.balatro.joker import Joker, JokerContext
from games.balatro.mechanics import ALL_CARDS_FACE


class PareidoliaJoker(Joker):
    mechanics = frozenset({ALL_CARDS_FACE})

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger not in {"", "HAND_RULES"}:
            return context
        context.data["all_cards_are_face"] = True
        return context
