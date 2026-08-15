from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.joker import Joker, JokerContext


class ZanyJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        if HandEvaluator().contains(
            context.cards,
            PokerHand.THREE_OF_A_KIND,
            rules=context.data.get("hand_rules"),
        ):
            context.score.mult += 12

        return context
