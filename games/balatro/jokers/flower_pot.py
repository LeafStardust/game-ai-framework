from games.balatro.joker import Joker, JokerContext


class FlowerPotJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        suits = {
            card.suit
            for card in context.cards
        }

        if {
            "Diamonds",
            "Clubs",
            "Hearts",
            "Spades",
        }.issubset(suits):
            context.score.x_mult *= 3

        return context