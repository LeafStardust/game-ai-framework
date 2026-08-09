from games.balatro.joker import Joker, JokerContext


class FlashCardJoker(Joker):

    def __init__(self):
        self.mult = 0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger == "SHOP_REROLLED":
            self.mult += 2
            return context

        if context.score is not None:
            context.score.mult += self.mult

        return context