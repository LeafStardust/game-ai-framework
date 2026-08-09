from games.balatro.joker import Joker, JokerContext


class FlatMultJoker(Joker):

    def __init__(
        self,
        mult: int
    ):
        self.mult = mult

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        context.score.mult += self.mult

        return context