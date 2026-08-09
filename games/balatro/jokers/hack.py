from games.balatro.joker import Joker, JokerContext


class HackJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        ranks = {"2", "3", "4", "5", "6", "7", "8", "9", "10"}

        context.data["retrigger_low_cards"] = sum(
            card.rank in ranks
            for card in context.cards
        )

        return context