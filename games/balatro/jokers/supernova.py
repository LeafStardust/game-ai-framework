from games.balatro.joker import Joker, JokerContext


class SupernovaJoker(Joker):

    def __init__(self, poker_hand):
        self.poker_hand = poker_hand
        self.mult = 0

    def apply(self, context: JokerContext) -> JokerContext:

        if context.poker_hand == self.poker_hand:
            self.mult += 1

        if context.score is not None:
            context.score.mult += self.mult

        return context