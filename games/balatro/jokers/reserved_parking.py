import random

from games.balatro.hand_rules import card_is_face
from games.balatro.joker import Joker, JokerContext


class ReservedParkingJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HELD_CARD":
            return context

        card = context.data.get("held_card")
        rules = context.data.get("hand_rules", {})
        if (
            card is None
            or bool(getattr(card, "debuffed", False))
            or not card_is_face(card, rules)
        ):
            return context

        if not bool(context.data.get("resolve_random_effects", True)):
            return context

        if random.random() < 0.5:
            context.state.money = (
                int(getattr(context.state, "money", 0) or 0)
                + 1
            )

        return context
