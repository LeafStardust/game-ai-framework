from games.balatro.joker import Joker, JokerContext


class ThrowbackJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "BLIND_SKIPPED":
            return context

        self.x_mult = getattr(self, "x_mult", 1.0) + 0.25

        return context