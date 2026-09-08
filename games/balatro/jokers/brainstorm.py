from games.balatro.joker import Joker, JokerContext
from games.balatro.mechanics import HAND_LEVEL_COPY


class BrainstormJoker(Joker):
    mechanics = frozenset({HAND_LEVEL_COPY})

    def apply(self, context: JokerContext) -> JokerContext:
        jokers = getattr(
            context.state,
            "jokers",
            []
        )

        if not jokers:
            return context

        context.data["copy_joker"] = jokers[0]

        return context
