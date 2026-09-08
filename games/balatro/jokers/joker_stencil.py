from games.balatro.joker import Joker, JokerContext


class JokerStencil(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        slots = max(0, int(getattr(context.state, "joker_slots", 5) or 0))
        non_stencil_jokers = sum(
            type(joker).__name__ != "JokerStencil"
            for joker in (getattr(context.state, "jokers", []) or [])
        )
        multiplier = max(slots - non_stencil_jokers, 1)
        context.score.x_mult *= multiplier

        return context
