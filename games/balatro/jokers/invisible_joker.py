from games.balatro.joker import Joker, JokerContext


class InvisibleJoker(Joker):

    def __init__(self):
        self.rounds = 0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "ROUND_ENDED":
            return context

        self.rounds += 1

        if self.rounds >= 2:
            context.data["invisible_joker_trigger"] = True
            self.rounds = 0

        return context