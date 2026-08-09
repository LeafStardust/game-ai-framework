from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext


class TheTribeJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.poker_hand in (
            PokerHand.FLUSH,
            PokerHand.STRAIGHT_FLUSH,
        ):
            context.score.x_mult *= 2

        return context