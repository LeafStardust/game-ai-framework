from games.balatro.joker import Joker, JokerContext


class SlyJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        ranks = [
            card.rank
            for card in context.cards
        ]

        if len(ranks) != len(set(ranks)):
            context.score.chips += 50

        return context