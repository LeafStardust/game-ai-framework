from games.balatro.joker import Joker, JokerContext


class GluttonousJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        mult = sum(
            card.suit == "Clubs"
            for card in context.cards
        ) * 3

        context.score.mult += mult

        return context