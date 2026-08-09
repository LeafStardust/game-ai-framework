from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext


class TheOrderJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.poker_hand in (
            PokerHand.STRAIGHT,
            PokerHand.STRAIGHT_FLUSH,
        ):
            context.score.x_mult *= 3

        return context