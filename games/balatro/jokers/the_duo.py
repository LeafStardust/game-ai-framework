from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext

class TheDuoJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        if context.poker_hand in (
            PokerHand.PAIR,
            PokerHand.TWO_PAIR,
            PokerHand.FULL_HOUSE,
            PokerHand.FOUR_OF_A_KIND,
        ):
            context.score.x_mult *= 2

        return context