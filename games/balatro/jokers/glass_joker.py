from games.balatro.joker import Joker, JokerContext


class GlassJoker(Joker):

    X_MULT_GAIN_PER_DESTROYED_GLASS = 0.75

    def __init__(self):
        self.x_mult = 1.0

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is None:
            return context

        context.score.x_mult *= self.x_mult

        return context

    def on_glass_destroyed(self, count: int = 1) -> None:
        destroyed = max(0, int(count))
        self.x_mult += self.X_MULT_GAIN_PER_DESTROYED_GLASS * destroyed
