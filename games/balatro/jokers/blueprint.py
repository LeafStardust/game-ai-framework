from games.balatro.joker import Joker, JokerContext
from games.balatro.mechanics import HAND_LEVEL_COPY


class BlueprintJoker(Joker):
    mechanics = frozenset({HAND_LEVEL_COPY})

    def apply(self, context: JokerContext) -> JokerContext:
        jokers = getattr(context.state, "jokers", [])

        try:
            index = jokers.index(self)
        except ValueError:
            return context

        if index + 1 < len(jokers):
            context.data["copy_joker"] = jokers[index + 1]

        return context
