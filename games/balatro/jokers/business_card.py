import random

from games.balatro.hand_rules import card_is_face
from games.balatro.joker import Joker, JokerContext


class BusinessCardJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "CARD_SCORED":
            return context

        card = context.data.get("current_scoring_card")
        rules = context.data.get("hand_rules", {})
        if card is None or not card_is_face(card, rules):
            return context

        if not bool(context.data.get("resolve_random_effects", True)):
            return context

        if random.random() < 0.5:
            context.state.money = (
                int(getattr(context.state, "money", 0) or 0)
                + 2
            )

        return context
