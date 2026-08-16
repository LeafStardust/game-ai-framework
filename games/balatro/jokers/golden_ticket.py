from games.balatro.joker import Joker, JokerContext


class GoldenTicketJoker(Joker):

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
