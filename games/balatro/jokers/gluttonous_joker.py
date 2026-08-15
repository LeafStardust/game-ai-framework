from games.balatro.hand_rules import card_matches_suit
from games.balatro.joker import Joker, JokerContext


class GluttonousJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        rules = context.data.get("hand_rules", {})
        scoring_cards = context.data.get("scoring_cards", context.cards)
        context.score.mult += 3 * sum(
            card_matches_suit(card, "Clubs", rules)
            for card in scoring_cards
        )
        return context
