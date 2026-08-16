from games.balatro.hand import PokerHand
from games.balatro.hand_evaluator import HandEvaluator
from games.balatro.joker import Joker, JokerContext


class SuperpositionJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context

        rules = context.data.get("hand_rules", {})
        cards = list(context.cards or [])
        evaluator = HandEvaluator()
        if not evaluator.contains(cards, PokerHand.STRAIGHT, rules=rules):
            return context

        straight_cards = evaluator.scoring_cards(
            PokerHand.STRAIGHT,
            cards,
            rules=rules,
        )
        if not any(str(getattr(card, "rank", "")) == "A" for card in straight_cards):
            return context

        context.data["create_tarot_count"] = (
            int(context.data.get("create_tarot_count", 0) or 0) + 1
        )
        return context
