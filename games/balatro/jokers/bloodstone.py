import random

from games.balatro.hand_rules import card_matches_suit
from games.balatro.joker import Joker, JokerContext


class BloodstoneJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None or context.trigger != "CARD_SCORED":
            return context

        card = context.data.get("current_scoring_card")
        rules = context.data.get("hand_rules", {})
        if card is None or not card_matches_suit(card, "Hearts", rules):
            return context

        projected_results = context.data.get("bloodstone_results")
        if projected_results is not None:
            try:
                success = bool(next(projected_results))
            except StopIteration:
                success = False
        elif bool(context.data.get("resolve_random_effects", True)):
            success = random.random() < 0.5
        else:
            success = False

        if success:
            context.score.x_mult *= 1.5

        return context
