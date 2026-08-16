from games.balatro.joker import Joker, JokerContext


class TradingCardJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "DISCARD":
            return context

        # Generic semantic probes historically omitted round-history context, so
        # absence keeps the standalone Joker behavior as a first-discard probe.
        # Live projection always supplies this flag explicitly.
        if not bool(context.data.get("first_discard", True)):
            return context

        if len(context.cards) != 1:
            return context

        context.data.setdefault(
            "destroyed_cards",
            []
        ).append(context.cards[0])

        context.data["money"] = int(context.data.get("money", 0) or 0) + 3
        context.state.money = (
            int(getattr(context.state, "money", 0) or 0) + 3
        )

        return context
