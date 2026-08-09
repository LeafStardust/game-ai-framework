from games.balatro.joker import Joker, JokerContext


class AcrobatJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        if context.data.get("hands_remaining") == 0:
            context.score.x_mult *= 3

        return context