from games.balatro.hand_rules import card_is_face
from games.balatro.joker import Joker, JokerContext


class FacelessJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "DISCARD":
            return context

        rules = context.data.get("hand_rules", {})
        face_cards = sum(
            card_is_face(card, rules)
            for card in context.cards
            if not card.debuffed
            and (not card.is_stone or rules.get("all_cards_are_face"))
        )

        if face_cards >= 3:
            context.state.money = (
                int(getattr(context.state, "money", 0) or 0)
                + 5
            )

        return context
