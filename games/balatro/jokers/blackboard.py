from games.balatro.hand_rules import card_matches_suit
from games.balatro.joker import Joker, JokerContext


class BlackboardJoker(Joker):
    mechanics = frozenset({"held_black_state_xmult"})

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        rules = context.data.get("hand_rules", {})
        if all(
            card_matches_suit(card, "Spades", rules)
            or card_matches_suit(card, "Clubs", rules)
            for card in context.held_cards
        ):
            context.score.x_mult *= 3

        return context
