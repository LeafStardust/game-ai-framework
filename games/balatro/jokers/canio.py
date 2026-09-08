from games.balatro.hand_rules import card_is_face
from games.balatro.joker import Joker, JokerContext


class CanioJoker(Joker):

    def __init__(self):
        self.x_mult = 1.0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        destroyed_cards = context.data.get("destroyed_cards", [])
        rules = context.data.get("hand_rules", {})
        faces_destroyed = sum(
            card_is_face(card, rules)
            for card in destroyed_cards
        )

        self.x_mult += faces_destroyed

        context.score.x_mult *= self.x_mult

        return context
