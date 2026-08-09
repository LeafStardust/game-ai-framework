from games.balatro.joker import Joker, JokerContext


class TradingCardJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "DISCARD":
            return context

        if len(context.cards) != 1:
            return context

        if context.data.get("trading_card_triggered"):
            return context

        context.data["trading_card_triggered"] = True
        context.data.setdefault(
            "destroyed_cards",
            []
        ).append(context.cards[0])

        context.data["money"] = (
            context.data.get("money", 0) + 3
        )

        return context