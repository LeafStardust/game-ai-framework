from __future__ import annotations

"""D2 retention authority for known FORMING strategies.

PINNED retention deliberately starts at mechanical commitment. That leaves a gap:
a known strategy can already have a defining core and explicit missing-piece plan
while still being FORMING, so ordinary local replacement value can repeatedly sell
the very core the planner is trying to complete.

This guard is intentionally narrower than pinned retention. It only protects an
existing FORMING StrategyPlan with a concrete strategy id, and only when the
replacement would destroy that plan outright. Replacements that preserve the same
forming strategy, mature it to PINNED, or establish a materially stronger PINNED
strategy remain allowed.
"""

from dataclasses import replace

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro.build_health_runtime import projected_state_with_jokers
from games.balatro.joker_policy import HOLD, REPLACE
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy


_MIN_PINNED_ESCAPE_GAIN = 2.0


def _candidate(composition, strategy_id: str | None):
    if not strategy_id:
        return None
    return next(
        (
            candidate
            for candidate in getattr(composition, "strategy_candidates", ()) or ()
            if candidate.strategy_id == strategy_id
        ),
        None,
    )


def _projected_jokers(state, candidate, index: int):
    jokers = list(getattr(state, "jokers", ()) or ())
    if index < 0 or index >= len(jokers):
        return None
    jokers[index] = candidate
    return tuple(jokers)


def apply_forming_strategy_retention(state, candidate, decision):
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

    current_plan = getattr(current_composition, "strategy_plan", None)
    if (
        current_plan is None
        or getattr(current_plan, "commitment", StrategyCommitment.EXPLORATORY)
        != StrategyCommitment.FORMING
        or not str(getattr(current_plan, "strategy_id", "") or "")
    ):
        return decision

    current_id = str(current_plan.strategy_id)
    projected_jokers = _projected_jokers(state, candidate, index)
    if projected_jokers is None:
        return decision
    projected_state = projected_state_with_jokers(state, projected_jokers)
    try:
        _, projected_composition = evaluate_bond_composition(projected_state)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return decision

    projected_plan = getattr(projected_composition, "strategy_plan", None)
    if projected_plan is not None and str(getattr(projected_plan, "strategy_id", "")) == current_id:
        # Keeping the same plan is fine whether it remains FORMING or matures.
        return decision

    projected_id = getattr(projected_composition, "pinned_strategy_id", None)
    projected_best = _candidate(projected_composition, projected_id)
    current_candidate = _candidate(current_composition, current_id)
    current_strength = float(getattr(current_candidate, "strength", getattr(current_plan, "strength", 0.0)) or 0.0)
    if (
        projected_best is not None
        and projected_best.commitment >= StrategyCommitment.PINNED
        and float(projected_best.strength) >= current_strength + _MIN_PINNED_ESCAPE_GAIN
    ):
        return replace(
            decision,
            rationale=(
                *getattr(decision, "rationale", ()),
                f"forming strategy pivot allowed: {current_id} strength={current_strength:.2f} -> {projected_best.strategy_id} strength={projected_best.strength:.2f}",
                f"required pinned escape gain={_MIN_PINNED_ESCAPE_GAIN:.2f}",
            ),
        )

    return replace(
        decision,
        action=HOLD,
        selected=None,
        rationale=(
            *getattr(decision, "rationale", ()),
            f"forming strategy retention veto: preserve {current_id} while explicit missing pieces are still being recruited",
            f"projected strategy={getattr(projected_plan, 'strategy_id', None) or projected_id or 'NONE'}",
            "do not churn away a defining FORMING core for an isolated local Joker upgrade",
        ),
    )


def install_forming_strategy_retention_policy() -> None:
    if getattr(PlaybookJokerAcquisitionPolicy, "_forming_strategy_retention_installed", False):
        return
    original_decide = PlaybookJokerAcquisitionPolicy.decide

    def decide(self, state, candidate):
        return apply_forming_strategy_retention(
            state,
            candidate,
            original_decide(self, state, candidate),
        )

    PlaybookJokerAcquisitionPolicy.decide = decide
    PlaybookJokerAcquisitionPolicy._forming_strategy_retention_installed = True
