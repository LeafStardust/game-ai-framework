from games.balatro.joker import Joker, JokerContext


class GluttonousJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        mult = sum(
            card.suit == "Clubs"
            for card in context.cards
        ) * 3

        context.score.mult += mult

        return context