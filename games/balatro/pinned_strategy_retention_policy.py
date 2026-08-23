from __future__ import annotations

"""D2 retention authority for mechanically pinned candidate strategies.

An engine can be strategically committed before its Bonds are highly ranked or
fully realized.  Replacements must therefore compare the current pinned mechanical
strategy with the projected post-replacement strategy instead of protecting only an
ACTIVE/MATURE power engine.
"""

from dataclasses import replace

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro.build_health_runtime import projected_state_with_jokers
from games.balatro.joker_policy import HOLD, REPLACE
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy


_MIN_STRATEGY_REPLACEMENT_GAIN = 2.0


def _candidate(composition, strategy_id: str | None):
    if not strategy_id:
        return None
    for candidate in getattr(composition, "strategy_candidates", ()) or ():
        if candidate.strategy_id == strategy_id:
            return candidate
    return None


def _projected_jokers(state, candidate, index: int):
    jokers = list(getattr(state, "jokers", ()) or ())
    if index < 0 or index >= len(jokers):
        return None
    jokers[index] = candidate
    return tuple(jokers)


def install_pinned_strategy_retention_policy() -> None:
    if getattr(PlaybookJokerAcquisitionPolicy, "_pinned_strategy_retention_installed", False):
        return

    original_decide = PlaybookJokerAcquisitionPolicy.decide

    def decide(self, state, candidate):
        decision = original_decide(self, state, candidate)
        if getattr(decision, "action", None) != REPLACE or getattr(decision, "selected", None) is None:
            return decision

        try:
            index = int(decision.selected.replace_index)
        except (AttributeError, TypeError, ValueError):
            return decision

        try:
            _, current_composition = evaluate_bond_composition(state)
        except (AttributeError, TypeError, ValueError, RuntimeError):
            return decision
        current_id = getattr(current_composition, "pinned_strategy_id", None)
        current = _candidate(current_composition, current_id)
        if current is None or current.commitment < StrategyCommitment.PINNED:
            return decision

        projected_jokers = _projected_jokers(state, candidate, index)
        if projected_jokers is None:
            return decision
        projected_state = projected_state_with_jokers(state, projected_jokers)
        try:
            _, projected_composition = evaluate_bond_composition(projected_state)
        except (AttributeError, TypeError, ValueError, RuntimeError):
            return decision

        projected_same = _candidate(projected_composition, current.strategy_id)
        if projected_same is not None and projected_same.commitment >= StrategyCommitment.PINNED:
            # The replacement preserves the strategy.  Lower confidence is allowed
            # because ordinary D2 economics still decided the transaction.
            return decision

        projected_id = getattr(projected_composition, "pinned_strategy_id", None)
        projected_best = _candidate(projected_composition, projected_id)
        if (
            projected_best is not None
            and projected_best.commitment >= StrategyCommitment.PINNED
            and float(projected_best.strength) >= float(current.strength) + _MIN_STRATEGY_REPLACEMENT_GAIN
        ):
            return replace(
                decision,
                rationale=(
                    *decision.rationale,
                    f"pinned strategy pivot allowed: {current.strategy_id} strength={current.strength:.2f} -> {projected_best.strategy_id} strength={projected_best.strength:.2f}",
                    f"required replacement strategy gain={_MIN_STRATEGY_REPLACEMENT_GAIN:.2f}",
                ),
            )

        return replace(
            decision,
            action=HOLD,
            selected=None,
            rationale=(
                *decision.rationale,
                f"pinned strategy retention veto: {current.strategy_id} commitment={current.commitment.name} confidence={current.confidence:.3f}",
                f"projected pinned strategy={projected_id or 'NONE'}",
                "do not dismantle a mechanically coherent pinned engine for an isolated local upgrade",
            ),
        )

    PlaybookJokerAcquisitionPolicy.decide = decide
    PlaybookJokerAcquisitionPolicy._pinned_strategy_retention_installed = True
