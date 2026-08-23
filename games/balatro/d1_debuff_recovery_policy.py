from __future__ import annotations

"""Bias D1 recovery discards away from currently debuffed playing cards.

Suit-debuff bosses such as The Head and The Window leave rank/suit identity intact,
so debuffed cards may still help form a poker hand.  They contribute no card chips,
enhancement/edition effects, or held effects, however.  The canonical retained-
structure heuristic did not distinguish them from active cards, which could make D1
preserve a dead-suit skeleton while burning every discard.

This policy adds only a bounded recovery preference.  It does not change play
scoring or hand classification, and it cannot make an otherwise illegal discard
legal.
"""

from games.balatro.live.hand_decision import LiveHandDecisionEvaluator


DISCARDED_DEBUFFED_CARD_BONUS = 12.0
RETAINED_DEBUFFED_CARD_PENALTY = 4.0


def _is_debuffed(evaluator: LiveHandDecisionEvaluator, card) -> bool:
    return bool(evaluator.scorer.is_card_debuffed(card))


def install_d1_debuff_recovery_policy() -> None:
    if getattr(LiveHandDecisionEvaluator, "_debuff_recovery_installed", False):
        return

    original_discard_value = LiveHandDecisionEvaluator._discard_value

    def discard_value(self, state, action, context):
        value = float(original_discard_value(self, state, action, context))
        if value <= -1_000_000.0:
            return value

        hand = tuple(getattr(state, "hand", ()) or ())
        if not any(_is_debuffed(self, card) for card in hand):
            return value

        discarded = tuple(getattr(action, "cards", ()) or ())
        discarded_ids = {id(card) for card in discarded}
        discarded_debuffed = sum(1 for card in discarded if _is_debuffed(self, card))
        retained_debuffed = sum(
            1
            for card in hand
            if id(card) not in discarded_ids and _is_debuffed(self, card)
        )

        return (
            value
            + discarded_debuffed * DISCARDED_DEBUFFED_CARD_BONUS
            - retained_debuffed * RETAINED_DEBUFFED_CARD_PENALTY
        )

    LiveHandDecisionEvaluator._discard_value = discard_value
    LiveHandDecisionEvaluator._debuff_recovery_installed = True
