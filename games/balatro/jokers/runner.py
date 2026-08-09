from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext


class RunnerJoker(Joker):

    def __init__(self):
        self.chips = 0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        if context.poker_hand != PokerHand.STRAIGHT:
            return context

        self.chips += 15
        context.score.chips += self.chips

        return context