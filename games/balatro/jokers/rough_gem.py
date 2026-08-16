from games.balatro.hand_rules import card_matches_suit
from games.balatro.joker import Joker, JokerContext


class RoughGemJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "CARD_SCORED":
            return context

        card = context.data.get("current_scoring_card")
        if card is None:
            return context

        rules = context.data.get("hand_rules", {})
        if not card_matches_suit(card, "Diamonds", rules):
            return context

        context.state.money = (
            int(getattr(context.state, "money", 0) or 0)
            + 1
        )
        return context
