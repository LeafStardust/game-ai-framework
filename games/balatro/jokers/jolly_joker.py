from games.balatro.joker import Joker, JokerContext


class JollyJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        if self._has_pair(context.cards):
            context.score.mult += 8

        return context

    @staticmethod
    def _has_pair(cards):
        ranks = [card.rank for card in cards]
        return len(ranks) != len(set(ranks))