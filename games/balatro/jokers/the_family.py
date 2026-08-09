from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext

class TheFamilyJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        if context.poker_hand == PokerHand.FOUR_OF_A_KIND:
            context.score.x_mult *= 4

        return context