from __future__ import annotations

"""Canonical post-freeze Joker coverage extensions.

These mappings were discovered only after the 46-Bond catalogue was frozen.
They reinforce existing Bonds; they do not create new Bonds. Source-level dedupe
prevents this layer from double-counting if an evaluator later absorbs a mapping.
"""

from games.balatro.bonds.model import BondContribution


def _append_once(parts, source: str, value: float):
    if any(getattr(p, "source", None) == source for p in parts):
        return list(parts)
    return [*parts, BondContribution(source, value)]


def apply_joker_coverage_extensions() -> None:
    from games.balatro.bonds import catalogue_batch_one as b1
    from games.balatro.bonds import catalogue_batch_two as b2
    from games.balatro.bonds import catalogue_batch_four as b4

    original_cash = b1.evaluate_cash_bond
    original_flush = b2.evaluate_flush_bond
    original_tarot = b4.evaluate_tarot_bond

    def evaluate_cash_bond(state):
        result = original_cash(state)
        jokers = list(getattr(state, "jokers", ()) or ())
        if not b1._contains_named(jokers, "cloud9joker", "cloud9"):
            return result
        parts = _append_once(result.contributions, "Cloud 9", 3.0)
        return b1._finish("cash", parts, b1.CASH_THRESHOLDS)

    def evaluate_flush_bond(state):
        result = original_flush(state)
        jokers = list(getattr(state, "jokers", ()) or ())
        if not b2._contains(jokers, "ancientjoker", "ancient"):
            return result
        parts = _append_once(result.contributions, "Ancient Joker", 4.0)
        return b2._finish("flush", parts, b2.FLUSH_THRESHOLDS, target="FLUSH")

    def evaluate_tarot_bond(state):
        result = original_tarot(state)
        jokers = list(getattr(state, "jokers", ()) or ())
        if not b4._contains(jokers, "8balljoker", "8ball"):
            return result
        parts = _append_once(result.contributions, "8 Ball", 2.0)
        return b4._finish("tarot", parts, b4.TAROT_THRESHOLDS)

    b1.evaluate_cash_bond = evaluate_cash_bond
    b1.BATCH_ONE_EVALUATORS["cash"] = evaluate_cash_bond
    b2.evaluate_flush_bond = evaluate_flush_bond
    b2.BATCH_TWO_EVALUATORS["flush"] = evaluate_flush_bond
    b4.evaluate_tarot_bond = evaluate_tarot_bond
    b4.BATCH_FOUR_EVALUATORS["tarot"] = evaluate_tarot_bond
