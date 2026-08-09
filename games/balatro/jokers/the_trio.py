from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext

class TheTrioJoker(Joker):

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        if context.poker_hand == PokerHand.THREE_OF_A_KIND:
            context.score.x_mult *= 3

        return context