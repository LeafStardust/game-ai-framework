from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext

class TheOrderJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        if context.poker_hand == PokerHand.STRAIGHT:
            context.score.x_mult *= 3

        return context