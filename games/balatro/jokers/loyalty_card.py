from games.balatro.joker import Joker, JokerContext


class LoyaltyCardJoker(Joker):

    def __init__(self):
        self.hands = 0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger == "HAND_PLAYED":
            self.hands += 1
            return context

        if (
            context.trigger == "HAND_SCORED"
            and context.score is not None
            and self.hands > 0
            and self.hands % 6 == 0
        ):
            context.score.x_mult *= 4

        return context
