from games.balatro.joker import Joker, JokerContext


class CanioJoker(Joker):

    def __init__(self):
        self.x_mult = 1.0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        destroyed_cards = context.data.get("destroyed_cards", [])

        faces_destroyed = sum(
            card.rank in {"J", "Q", "K"}
            for card in destroyed_cards
        )

        self.x_mult += faces_destroyed

        context.score.x_mult *= self.x_mult

        return context