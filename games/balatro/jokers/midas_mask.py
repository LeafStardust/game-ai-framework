from games.balatro.hand_rules import card_is_face
from games.balatro.joker import Joker, JokerContext


class MidasMaskJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger == "HAND_PLAYED":
            return self._goldify_scoring_faces(context)

        # Preserve the legacy direct HAND_SCORED probe without reapplying the
        # transformation during live scoring, where HAND_PLAYED already handled
        # the before-score timing and scorer contexts carry scoring_cards.
        if (
            context.trigger == "HAND_SCORED"
            and "scoring_cards" not in context.data
        ):
            return self._goldify_scoring_faces(context)

        return context

    @staticmethod
    def _goldify_scoring_faces(context: JokerContext) -> JokerContext:
        scoring_cards = context.data.get("scoring_cards")
        if not isinstance(scoring_cards, (list, tuple)):
            scoring_cards = context.cards
        rules = context.data.get("hand_rules")

        for card in scoring_cards:
            if bool(getattr(card, "debuffed", False)):
                continue
            if card_is_face(card, rules):
                card.enhancement = "Gold"

        return context
