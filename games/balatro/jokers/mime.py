from games.balatro.joker import Joker, JokerContext
from games.balatro.mechanics import RETRIGGER_HELD_CARDS


class MimeJoker(Joker):

    mechanics = frozenset({RETRIGGER_HELD_CARDS})

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger not in {"", "HAND_PLAYED"}:
            return context

        context.data["retrigger_held_abilities"] = (
            int(context.data.get("retrigger_held_abilities", 0) or 0) + 1
        )

        return context
