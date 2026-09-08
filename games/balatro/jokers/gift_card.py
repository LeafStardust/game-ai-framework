from games.balatro.joker import Joker, JokerContext


class GiftCardJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "ROUND_ENDED":
            return context

        for card in context.data.get("owned_cards", []):
            card.sell_value = getattr(card, "sell_value", 0) + 1

        return context