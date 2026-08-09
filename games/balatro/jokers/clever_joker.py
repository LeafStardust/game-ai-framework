from collections import Counter

from games.balatro.joker import Joker, JokerContext


class CleverJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        counts = Counter(
            card.rank
            for card in context.cards
        )

        pairs = sum(
            count >= 2
            for count in counts.values()
        )

        if pairs >= 2:
            context.score.chips += 80

        return context