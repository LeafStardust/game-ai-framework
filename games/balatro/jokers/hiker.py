from games.balatro.joker import Joker, JokerContext
from games.balatro.scoring import BalatroScorer


class HikerJoker(Joker):

    def apply(self, context: JokerContext) -> JokerContext:
        if context.trigger != "HAND_SCORED":
            return context

        scoring_cards = context.data.get("scoring_cards")
        if not isinstance(scoring_cards, (list, tuple)):
            scoring_cards = context.cards

        global_retriggers = max(
            0,
            int(context.data.get("retrigger_played_cards", 0) or 0),
        )
        for card in scoring_cards:
            if bool(getattr(card, "debuffed", False)):
                continue

            triggers = BalatroScorer._played_card_trigger_count(
                card,
                global_retriggers,
            )
            if triggers <= 0:
                continue

            # The card's existing permanent bonus is scored by BalatroScorer on
            # every activation. Hiker itself resolves after each scored-card
            # activation, so only earlier Hiker activations can increase chips
            # on a later retrigger of the same card in this hand.
            if context.score is not None and triggers > 1:
                context.score.chips += 5 * triggers * (triggers - 1) // 2

            card.permanent_bonus = (
                int(getattr(card, "permanent_bonus", 0) or 0)
                + 5 * triggers
            )

        return context
