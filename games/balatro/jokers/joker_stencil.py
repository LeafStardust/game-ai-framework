from games.balatro.joker import Joker, JokerContext


class JokerStencil(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        joker_slots = context.data.get(
            "joker_slots",
            5
        )

        occupied = len(
            getattr(context.state, "jokers", [])
        )

        empty = max(
            joker_slots - occupied,
            0
        )

        context.score.x_mult *= max(
            empty,
            1
        )

        return context