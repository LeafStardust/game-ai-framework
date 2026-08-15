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
        if context.trigger == "HELD_CARD":
            if context.score is None:
                return context
            card = context.data.get("held_card")
            lowest = context.data.get("lowest_held_card")
            if card is None or card is not lowest:
                return context
            value = self.RANK_VALUES[card.rank] * 2
            context.score.mult += value
            context.data["raised_fist_card"] = card
            context.data["raised_fist_mult"] = value
            return context

        if context.trigger not in {"", "HAND_SCORED"}:
            return context
        if not context.held_cards:
            return context

        lowest = min(
            context.held_cards,
            key=lambda card: self.RANK_VALUES[card.rank],
        )
        value = self.RANK_VALUES[lowest.rank] * 2
        context.data["raised_fist_card"] = lowest
        context.data["raised_fist_mult"] = value
        if context.trigger == "" and context.score is not None:
            context.score.mult += value
        return context
