from games.balatro.joker import Joker, JokerContext


class PhotographJoker(Joker):

    FACE_RANKS = {"J", "Q", "K"}

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        if context.trigger == "CARD_SCORED":
            current = context.data.get("current_scoring_card")
            first_face = context.data.get("first_scoring_face_card")
            if (
                current is not None
                and current is first_face
                and current.rank in self.FACE_RANKS
            ):
                context.score.x_mult *= 2
            return context

        # Preserve standalone semantic probes outside the explicit card-by-card
        # scorer. Photograph targets the first face card that actually scores.
        scoring_cards = context.data.get("scoring_cards", context.cards)
        first_face = next(
            (
                card
                for card in scoring_cards
                if card.rank in self.FACE_RANKS
            ),
            None,
        )
        if first_face is not None:
            context.score.x_mult *= 2

        return context
