from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.joker import Joker, JokerContext


class CraftyJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is None:
            return context

        if HandEvaluator().contains(
            context.cards,
            PokerHand.FLUSH,
            rules=context.data.get("hand_rules"),
        ):
            context.score.chips += 80

        return context
