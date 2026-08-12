from games.balatro.joker import Joker, JokerContext


class VampireJoker(Joker):

    def __init__(self):
        self.x_mult = 1.0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger == "HAND_PLAYED":
            scoring_cards = context.data.get("scoring_cards", context.cards)
            enhanced_cards = [
                card
                for card in scoring_cards
                if card.enhancement is not None
            ]

            for card in enhanced_cards:
                card.enhancement = None

            self.x_mult += 0.1 * len(enhanced_cards)
            return context

        if context.score is not None:
            context.score.x_mult *= self.x_mult

        return context
