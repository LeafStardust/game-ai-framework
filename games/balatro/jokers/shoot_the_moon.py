from games.balatro.joker import Joker, JokerContext


class ShootTheMoonJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:

        if context.score is None:
            return context

        queens = sum(
            card.rank == "Q"
            for card in context.cards
        )

        context.score.mult += queens * 13

        return context