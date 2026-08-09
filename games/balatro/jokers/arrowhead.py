from games.balatro.joker import Joker, JokerContext


class ArrowheadJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:

        if context.score is None:
            return context

        spades = sum(
            card.suit == "Spades"
            for card in context.cards
        )

        context.score.chips += spades * 50

        return context