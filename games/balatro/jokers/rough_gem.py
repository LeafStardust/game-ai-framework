from games.balatro.joker import Joker, JokerContext


class RoughGemJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:

        diamonds = sum(
            card.suit == "Diamonds"
            for card in context.cards
        )

        context.data["money"] = (
            context.data.get("money", 0)
            + diamonds
        )

        return context