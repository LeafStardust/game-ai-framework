from games.balatro.joker import Joker, JokerContext


class LustyJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        context.score.mult += sum(
            card.suit == "Hearts"
            for card in context.cards
        ) * 3

        return context