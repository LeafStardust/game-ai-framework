from games.balatro.joker import Joker, JokerContext


class VampireJoker(Joker):

    def __init__(self):
        self.x_mult = 1.0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger == "HAND_PLAYED":
            self._consume_scoring_enhancements(context)
            return context

        if context.trigger == "HAND_SCORED":
            if context.score is not None:
                context.score.x_mult *= self.x_mult
            return context

        # Preserve the original combined behavior for standalone semantic probes
        # that do not model explicit hand-play/hand-score phases.
        self._consume_scoring_enhancements(context)
        if context.score is not None:
            context.score.x_mult *= self.x_mult
        return context

    def _consume_scoring_enhancements(self, context: JokerContext) -> None:
        scoring_cards = context.data.get("scoring_cards", context.cards)
        enhanced_cards = [
            card
            for card in scoring_cards
            if card.enhancement is not None
        ]

        for card in enhanced_cards:
            card.enhancement = None

        self.x_mult += 0.1 * len(enhanced_cards)
