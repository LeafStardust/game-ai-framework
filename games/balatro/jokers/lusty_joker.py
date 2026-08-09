from games.balatro.joker import Joker, JokerContext


class LustyJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        mult = sum(
            card.suit == "Hearts"
            for card in context.cards
        ) * 3

        context.score.mult += mult

        return context