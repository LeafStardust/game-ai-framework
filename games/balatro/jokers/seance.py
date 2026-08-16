from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext


class SeanceJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context
        if context.poker_hand != PokerHand.STRAIGHT_FLUSH:
            return context

        context.data["create_spectral_count"] = (
            int(context.data.get("create_spectral_count", 0) or 0) + 1
        )
        return context
