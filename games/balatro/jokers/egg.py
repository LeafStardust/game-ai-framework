from games.balatro.joker import Joker, JokerContext


class EggJoker(Joker):

    def __init__(self):
        self.sell_value = 3

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger == "ROUND_ENDED":
            self.sell_value += 3

        return context