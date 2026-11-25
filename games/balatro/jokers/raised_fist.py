from games.balatro.joker import Joker, JokerContext
from games.balatro.hand_evaluator import HandEvaluator


class RaisedFistJoker(Joker):
    mechanics = frozenset({"held_lowest_rank_payoff"})

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

    @staticmethod
    def lowest_held_target(cards):
        """Select the rightmost lowest base rank before checking for debuff."""
        rank_order = HandEvaluator.RANK_ORDER
        return min(
            (
                card for card in reversed(cards)
                if getattr(card, "enhancement", None) != "Stone"
                and card.rank in rank_order
            ),
            key=lambda card: rank_order[card.rank],
            default=None,
        )

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger == "HELD_CARD":
            if context.score is None:
                return context
            card = context.data.get("held_card")
            lowest = context.data.get("lowest_held_card")
            if card is None or card is not lowest or getattr(card, "debuffed", False):
                return context
            value = self.RANK_VALUES[card.rank] * 2
            context.score.mult += value
            context.data["raised_fist_card"] = card
            context.data["raised_fist_mult"] = value
            return context

        if context.trigger not in {"", "HAND_SCORED"}:
            return context
        lowest = self.lowest_held_target(context.held_cards)
        if lowest is None or getattr(lowest, "debuffed", False):
            return context
        value = self.RANK_VALUES[lowest.rank] * 2
        context.data["raised_fist_card"] = lowest
        context.data["raised_fist_mult"] = value
        if context.trigger == "" and context.score is not None:
            context.score.mult += value
        return context
