from __future__ import annotations

"""Reject Joker acquisitions that introduce a new canonical Bond conflict.

Composition conflicts are strategic incompatibilities, not merely diagnostic score
penalties. A shop candidate may strengthen a new Bond and still be a bad acquisition
when that Bond directly conflicts with an already-realized direction. D2 therefore
must not reward fresh structural progress strongly enough to create a new unresolved
conflict.

Legitimate pivots remain possible: replacing an incumbent may remove the old side of
the conflict, in which case the projected composition contains no newly introduced
conflict and this guard does not veto the transition.
"""

import copy
from dataclasses import replace

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.joker_policy import BUY, HOLD, REPLACE
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy


def _conflict_set(composition) -> frozenset[frozenset[str]]:
    return frozenset(
        frozenset((str(left), str(right)))
        for left, right in tuple(getattr(composition, "conflicts", ()) or ())
        if str(left) and str(right) and str(left) != str(right)
    )


def _projected_state(state, candidate, decision):
    projected = copy.copy(state)
    projected.jokers = list(getattr(state, "jokers", ()) or ())
    action = getattr(decision, "action", None)
    if action == BUY:
        projected.jokers.append(candidate)
        return projected
    if action == REPLACE and getattr(decision, "selected", None) is not None:
        try:
            index = int(decision.selected.replace_index)
        except (AttributeError, TypeError, ValueError):
            return None
        if index < 0 or index >= len(projected.jokers):
            return None
        projected.jokers[index] = candidate
        return projected
    return None


def _format_conflict(pair: frozenset[str]) -> str:
    return " <> ".join(sorted(pair))


def install_bond_conflict_admission_policy() -> None:
    if getattr(PlaybookJokerAcquisitionPolicy, "_bond_conflict_admission_installed", False):
        return

    original_decide = PlaybookJokerAcquisitionPolicy.decide

    def decide(self, state, candidate):
        decision = original_decide(self, state, candidate)
        if getattr(decision, "action", None) not in {BUY, REPLACE}:
            return decision

        projected = _projected_state(state, candidate, decision)
        if projected is None:
            return decision

        try:
            _, before = evaluate_bond_composition(state)
            _, after = evaluate_bond_composition(projected)
        except (AttributeError, TypeError, ValueError, RuntimeError):
            return decision

        new_conflicts = _conflict_set(after) - _conflict_set(before)
        if not new_conflicts:
            return decision

        conflicts_text = ", ".join(
            _format_conflict(pair)
            for pair in sorted(new_conflicts, key=lambda item: tuple(sorted(item)))
        )
        return replace(
            decision,
            action=HOLD,
            selected=None,
            rationale=(
                *tuple(getattr(decision, "rationale", ()) or ()),
                f"canonical Bond conflict veto: acquisition introduces {conflicts_text}",
                "new Bond progress cannot override an unresolved conflict with the current build direction",
            ),
        )

    PlaybookJokerAcquisitionPolicy.decide = decide
    PlaybookJokerAcquisitionPolicy._bond_conflict_admission_installed = True
