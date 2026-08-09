from games.balatro.joker import Joker, JokerContext


class GreedyJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        mult = sum(
            card.suit == "Diamonds"
            for card in context.cards
        ) * 3

        context.score.mult += mult

        return context