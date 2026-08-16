from games.balatro.joker import Joker, JokerContext


class FlatMultJoker(Joker):

    def __init__(
        self,
        mult: int = 4
    ):
        # Canonical base "Joker" is the ordinary +4 Mult Joker. Keeping the
        # parameter overridable preserves this small reusable model while making
        # the playable base Joker constructible without invented live metadata.
        self.mult = mult

    def apply(
        self,
        context: JokerContext
    ) -> JokerContext:

        if context.score is not None:
            context.score.mult += self.mult

        return context
