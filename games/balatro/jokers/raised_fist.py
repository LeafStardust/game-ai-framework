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
        if context.trigger != "HAND_SCORED":
            return context

        if not context.held_cards:
            return context

        lowest = min(
            context.held_cards,
            key=lambda card: self.RANK_VALUES[card.rank]
        )

        context.data["raised_fist_card"] = lowest
        context.data["raised_fist_mult"] = (
            self.RANK_VALUES[lowest.rank] * 2
        )

        return context