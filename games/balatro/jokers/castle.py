from games.balatro.hand_rules import card_matches_suit
from games.balatro.joker import Joker, JokerContext


class CastleJoker(Joker):

    def __init__(self, suit: str):
        self.suit = suit
        self.chips = 0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.event is not None:
            cards = context.event.cards or []

            if context.event.type.value == "CARDS_DISCARDED":
                rules = context.data.get("hand_rules", {})
                matching_cards = sum(
                    not bool(getattr(card, "debuffed", False))
                    and card_matches_suit(card, self.suit, rules)
                    for card in cards
                )

                self.chips += matching_cards * 3
                return context

        if context.score is not None:
            context.score.chips += self.chips

        return context
