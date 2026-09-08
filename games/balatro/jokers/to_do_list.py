from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext


class ToDoListJoker(Joker):
    REWARD = 4

    def __init__(self, target_hand: str | PokerHand | None = None):
        self.target_hand = self._normalize_hand(target_hand)

    def set_target_hand(self, target_hand: str | PokerHand | None) -> None:
        """Update the public target when authoritative round state changes."""
        self.target_hand = self._normalize_hand(target_hand)

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED" or context.poker_hand is None:
            return context
        if self.target_hand is None or context.poker_hand != self.target_hand:
            return context

        if context.state is not None:
            context.state.money = (
                int(getattr(context.state, "money", 0) or 0)
                + self.REWARD
            )

        # Preserve the semantic-analysis/economy channel as well. This is metadata;
        # the branch-state mutation above is authoritative for live projection.
        context.data["money"] = int(context.data.get("money", 0) or 0) + self.REWARD
        return context

    @staticmethod
    def _normalize_hand(value: str | PokerHand | None) -> PokerHand | None:
        if isinstance(value, PokerHand):
            return value
        if not isinstance(value, str) or not value.strip():
            return None

        normalized = value.strip().upper().replace(" ", "_").replace("-", "_")
        aliases = {
            "HIGHCARD": "HIGH_CARD",
            "TWOPAIR": "TWO_PAIR",
            "THREEOFAKIND": "THREE_OF_A_KIND",
            "FOUROFAKIND": "FOUR_OF_A_KIND",
            "FULLHOUSE": "FULL_HOUSE",
            "STRAIGHTFLUSH": "STRAIGHT_FLUSH",
        }
        normalized = aliases.get(normalized.replace("_", ""), normalized)
        try:
            return PokerHand[normalized]
        except KeyError:
            return None
