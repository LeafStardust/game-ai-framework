from games.balatro.joker import Joker, JokerContext


class WeeJoker(Joker):

    def __init__(self):
        self.chips = 0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        scoring_cards = context.data.get("scoring_cards", context.cards)
        twos = sum(
            card.rank == "2"
            for card in scoring_cards
        )

        self.chips += twos * 8
        context.score.chips += self.chips

        return context
