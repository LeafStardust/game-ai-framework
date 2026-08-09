from games.balatro.joker import Joker, JokerContext


class RaisedFistJoker(Joker):

    RANK_VALUES = {
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
        "10": 10,
        "J": 10,
        "Q": 10,
        "K": 10,
        "A": 11,
    }

    def apply(self, context: JokerContext) -> JokerContext:

        if context.score is None or not context.held_cards:
            return context

        lowest = min(
            self.RANK_VALUES[card.rank]
            for card in context.held_cards
        )

        context.score.mult += lowest * 2

        return context