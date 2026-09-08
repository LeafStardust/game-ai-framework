from games.balatro.joker import Joker, JokerContext
from games.balatro.mechanics import GOLD_CARD_SCORING_ECONOMY


class GoldenTicketJoker(Joker):
    mechanics = frozenset({GOLD_CARD_SCORING_ECONOMY})

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "CARD_SCORED":
            return context

        card = context.data.get("current_scoring_card")
        if card is None or getattr(card, "enhancement", None) != "Gold":
            return context

        context.state.money = (
            int(getattr(context.state, "money", 0) or 0)
            + 4
        )
        return context
