from games.balatro.joker import Joker, JokerContext


class CraftyJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.cards and len({
            card.suit
            for card in context.cards
        }) == 1:
            context.score.chips += 80

        return context