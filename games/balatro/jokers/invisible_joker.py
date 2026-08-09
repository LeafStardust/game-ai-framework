from games.balatro.joker import Joker, JokerContext


class InvisibleJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "ROUND_ENDED":
            return context

        self.rounds = getattr(self, "rounds", 0) + 1

        if self.rounds >= 2:
            context.data["invisible_joker_trigger"] = True
            self.rounds = 0

        return context