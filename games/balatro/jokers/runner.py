from games.balatro.hand import PokerHand
from games.balatro.joker import Joker, JokerContext


class RunnerJoker(Joker):

    def __init__(self):
        self.chips = 0

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger == "HAND_PLAYED":
            if context.data["contains_straight"]:
                self.chips += 15
            return context

        if context.trigger == "" and context.score is not None:
            # Standalone probes may provide only the already classified hand.
            if context.poker_hand in {PokerHand.STRAIGHT, PokerHand.STRAIGHT_FLUSH}:
                self.chips += 15
        if context.trigger in {"", "HAND_SCORED"} and context.score is not None:
            context.score.chips += self.chips
        return context
