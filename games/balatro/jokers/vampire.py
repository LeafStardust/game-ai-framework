from games.balatro.joker import Joker, JokerContext


class VampireJoker(Joker):

    def __init__(self):
        self.x_mult = 1.0

    def apply(self, context: JokerContext) -> JokerContext:

        enhanced_cards = [
            card
            for card in context.cards
            if card.enhancement is not None
        ]

        for card in enhanced_cards:
            card.enhancement = None

        self.x_mult += 0.1 * len(enhanced_cards)

        if context.score is not None:
            context.score.x_mult *= self.x_mult

        return context