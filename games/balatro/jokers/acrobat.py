from games.balatro.joker import Joker, JokerContext


class AcrobatJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        if int(getattr(context.state, "hands_remaining", 0) or 0) <= 1:
            context.score.x_mult *= 3

        return context
