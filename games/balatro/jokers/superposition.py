from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext


class SuperpositionJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context

        has_ace = any(
            card.rank == "A"
            for card in context.cards
        )

        if has_ace and context.poker_hand == PokerHand.STRAIGHT:
            context.data.setdefault(
                "created_tarot_cards",
                []
            ).append("Random")

        return context