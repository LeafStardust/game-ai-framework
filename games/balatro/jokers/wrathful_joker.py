from games.balatro.joker import Joker, JokerContext


class WrathfulJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        mult = sum(
            card.suit == "Spades"
            for card in context.cards
        ) * 3

        context.score.mult += mult

        return context