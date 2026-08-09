from games.balatro.joker import Joker, JokerContext


class BullJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        context.score.mult += (
            (context.state.money // 5) * 2
        )

        return context