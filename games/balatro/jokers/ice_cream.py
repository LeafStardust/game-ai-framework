from games.balatro.joker import Joker, JokerContext


class IceCreamJoker(Joker):

    def __init__(self):
        self.chips = 100

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is not None:
            context.score.chips += self.chips

        if context.trigger == "HAND_SCORED":
            self.chips = max(self.chips - 5, 0)

        return context