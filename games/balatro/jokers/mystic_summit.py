from games.balatro.joker import Joker, JokerContext


class MysticSummitJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        if int(getattr(context.state, "discards_remaining", 0) or 0) == 0:
            context.score.mult += 15

        return context
