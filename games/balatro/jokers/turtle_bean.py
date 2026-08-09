from games.balatro.joker import Joker, JokerContext


class TurtleBeanJoker(Joker):

    def __init__(self):
        self.hand_size = 5

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger == "ROUND_STARTED":
            self.hand_size = max(self.hand_size - 1, 0)

        context.data["hand_size_modifier"] = self.hand_size

        return context