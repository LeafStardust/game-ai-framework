from games.balatro.joker import Joker, JokerContext


class GoldenTicketJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "CARDS_SCORED":
            return context

        gold_cards = sum(
            card.enhancement == "Gold"
            for card in context.cards
        )

        context.data["money"] = (
            context.data.get("money", 0)
            + gold_cards * 4
        )

        return context