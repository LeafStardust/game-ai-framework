from collections import Counter

from games.balatro.joker import Joker, JokerContext

class ZanyJoker(Joker):

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

        if any(count >= 3 for count in counts.values()):
            context.score.mult += 12

        return context