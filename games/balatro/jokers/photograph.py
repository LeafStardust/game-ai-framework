from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.hand_rules import card_is_face
from games.balatro.joker import Joker, JokerContext


class PhotographJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        rules = context.data.get("hand_rules", {})

        if context.trigger == "CARD_SCORED":
            current = context.data.get("current_scoring_card")
            scoring_cards = HandEvaluator().scoring_cards(
                context.poker_hand,
                list(context.cards or []),
                rules=rules,
            )
            first_face = next(
                (
                    card
                    for card in scoring_cards
                    if not getattr(card, "debuffed", False)
                    and card_is_face(card, rules)
                ),
                None,
            )
            if current is not None and current is first_face:
                context.score.x_mult *= 2
            return context

        # Preserve standalone semantic probes outside the explicit card-by-card
        # scorer. Photograph targets the first face card that actually scores.
        scoring_cards = context.data.get("scoring_cards", context.cards)
        first_face = next(
            (
                card
                for card in scoring_cards
                if not getattr(card, "debuffed", False)
                and card_is_face(card, rules)
            ),
            None,
        )
        if first_face is not None:
            context.score.x_mult *= 2

        return context
