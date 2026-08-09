from games.balatro.joker import Joker, JokerContext


class TheIdolJoker(Joker):

    def __init__(
        self,
        rank: str,
        suit: str
    ):
        self.rank = rank
        self.suit = suit

    def apply(self, context: JokerContext) -> JokerContext:

        if context.score is None:
            return context

        matches = sum(
            card.rank == self.rank
            and card.suit == self.suit
            for card in context.cards
        )

        context.score.x_mult *= 2 ** matches

        return context