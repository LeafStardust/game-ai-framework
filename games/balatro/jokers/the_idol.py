from games.balatro.hand_rules import card_matches_suit
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

        rules = context.data.get("hand_rules", {})
        scoring_cards = context.data.get("scoring_cards", context.cards)
        matches = sum(
            str(getattr(card, "rank", "")) == self.rank
            and card_matches_suit(card, self.suit, rules)
            for card in scoring_cards
        )
        context.score.x_mult *= 2 ** matches
        return context
