from games.balatro.hand_rules import card_matches_suit
from games.balatro.joker import Joker, JokerContext


class FlowerPotJoker(Joker):

    REQUIRED_SUITS = (
        "Hearts",
        "Diamonds",
        "Clubs",
        "Spades",
    )

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        scoring_cards = list(
            context.data.get("scoring_cards", context.cards)
            or []
        )
        if len(scoring_cards) < len(self.REQUIRED_SUITS):
            return context

        rules = context.data.get("hand_rules", {})
        if self._covers_required_suits(scoring_cards, rules):
            context.score.x_mult *= 3

        return context

    @classmethod
    def _covers_required_suits(cls, cards, rules: dict) -> bool:
        """Require one distinct scoring card for each required suit."""
        used: set[int] = set()

        def assign(suit_index: int) -> bool:
            if suit_index >= len(cls.REQUIRED_SUITS):
                return True

            suit = cls.REQUIRED_SUITS[suit_index]
            for index, card in enumerate(cards):
                if index in used:
                    continue
                if not card_matches_suit(card, suit, rules):
                    continue
                used.add(index)
                if assign(suit_index + 1):
                    return True
                used.remove(index)
            return False

        return assign(0)
