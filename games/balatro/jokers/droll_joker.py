from games.balatro.joker import Joker, JokerContext


class DrollJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.cards and len({
            card.suit
            for card in context.cards
        }) == 1:
            context.score.mult += 10

        return context