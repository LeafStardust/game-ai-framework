from games.balatro.joker import Joker, JokerContext


class WeeJoker(Joker):

    def __init__(self):
        self.chips = 0

    def apply(self, context: JokerContext) -> JokerContext:
        twos = sum(
            card.rank == "2"
            for card in context.cards
        )

        self.chips += twos * 8
        context.score.chips += self.chips

        return context