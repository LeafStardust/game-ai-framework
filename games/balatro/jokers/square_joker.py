from games.balatro.joker import Joker, JokerContext


class SquareJoker(Joker):

    def __init__(self):
        self.chips = 0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context

        if len(context.cards) == 4:
            self.chips += 4

        if context.score is not None:
            context.score.chips += self.chips

        return context