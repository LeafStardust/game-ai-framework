from games.balatro.joker import Joker, JokerContext


class HalfJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        if len(context.cards) <= 3:
            context.score.mult += 20

        return context
