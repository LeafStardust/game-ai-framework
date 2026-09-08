from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext


class SpareTrousersJoker(Joker):

    def __init__(self):
        self.mult = 0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context

        if context.poker_hand == PokerHand.TWO_PAIR:
            self.mult += 2

        if context.score is not None:
            context.score.mult += self.mult

        return context