from games.balatro.joker import Joker, JokerContext


class Cloud9Joker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "ROUND_ENDED":
            return context

        deck = context.data.get("deck", [])

        nines = sum(
            card.rank == "9"
            for card in deck
        )

        context.data["money"] = (
            context.data.get("money", 0) + nines
        )

        return context