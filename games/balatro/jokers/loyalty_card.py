from games.balatro.joker import Joker, JokerContext


class LoyaltyCardJoker(Joker):

    def __init__(self):
        self.hands = 0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        self.hands += 1

        if self.hands % 6 == 0:
            context.score.x_mult *= 4

        return context