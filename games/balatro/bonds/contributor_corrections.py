from __future__ import annotations

"""Post-catalogue contributor corrections discovered by full Joker coverage review."""

from games.balatro.bonds.model import BondContribution


def apply_contributor_corrections() -> None:
    from games.balatro.bonds import catalogue_batch_two as b2

    original_two_pair = b2.evaluate_two_pair_bond
    original_deck_thinning = b2.evaluate_deck_thinning_bond

    def evaluate_two_pair_bond(state):
        result = original_two_pair(state)
        jokers = list(getattr(state, "jokers", ()) or ())
        if not b2._contains(jokers, "squarejoker"):
            return result
        parts = list(result.contributions) + [BondContribution("Square Joker four-card bridge", 3.0)]
        return b2._finish("two_pair", parts, b2.TWO_PAIR_THRESHOLDS, target="TWO_PAIR")

    def evaluate_deck_thinning_bond(state):
        result = original_deck_thinning(state)
        jokers = list(getattr(state, "jokers", ()) or ())
        if not b2._contains(jokers, "erosion"):
            return result
        parts = list(result.contributions) + [BondContribution("Erosion thinning payoff", 7.0)]
        return b2._finish("deck_thinning", parts, b2.DECK_THINNING_THRESHOLDS)

    b2.evaluate_two_pair_bond = evaluate_two_pair_bond
    b2.evaluate_deck_thinning_bond = evaluate_deck_thinning_bond
    b2.BATCH_TWO_EVALUATORS["two_pair"] = evaluate_two_pair_bond
    b2.BATCH_TWO_EVALUATORS["deck_thinning"] = evaluate_deck_thinning_bond
