from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext


class SeanceJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context
        if context.poker_hand != PokerHand.STRAIGHT_FLUSH:
            return context

        # Category marker only; live projection resolves random identity separately.
        context.data.setdefault("created_consumables", []).append("Spectral")
        return context
