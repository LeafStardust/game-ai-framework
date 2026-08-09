from collections import Counter

from games.balatro.joker import Joker, JokerContext


class MadJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        counts = Counter(
            card.rank
            for card in context.cards
        )

        pairs = sum(
            count >= 2
            for count in counts.values()
        )

        if pairs >= 2:
            context.score.mult += 10

        return context