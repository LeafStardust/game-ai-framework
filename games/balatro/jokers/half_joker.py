from games.balatro.joker import Joker, JokerContext


class HalfJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if len(context.cards) <= 3:
            context.score.mult += 20

        return context