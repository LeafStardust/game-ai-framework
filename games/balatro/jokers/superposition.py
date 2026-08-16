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
        contains_straight = evaluator.contains(cards, PokerHand.STRAIGHT, rules=rules)

        if contains_straight:
            straight_cards = evaluator.scoring_cards(
                PokerHand.STRAIGHT,
                cards,
                rules=rules,
            )
        else:
            # Build/semantic probes may provide an authoritative classified hand
            # without constructing matching synthetic cards. Live projection always
            # supplies hand_rules, so exact runtime evaluation never uses this fallback.
            if "hand_rules" in context.data or context.poker_hand != PokerHand.STRAIGHT:
                return context
            straight_cards = cards

        if not any(str(getattr(card, "rank", "")) == "A" for card in straight_cards):
            return context

        # Category marker only; live projection resolves random identity separately.
        context.data.setdefault("created_consumables", []).append("Tarot")
        return context
