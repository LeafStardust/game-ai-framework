from __future__ import annotations

import copy
from dataclasses import replace

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.build import JokerBuildTransitionPlanner
from games.balatro.joker_policy import (
    HOLD,
    REPLACE,
    JokerAcquisitionDecision,
    JokerAcquisitionPolicy,
    JokerAcquisitionThresholds,
)
from games.balatro.playbook import BalatroPlaybookNotFound, default_balatro_playbooks
from games.balatro.state import BalatroState


def _joker_token(joker: object) -> str:
    value = (
        getattr(joker, "name", None)
        or getattr(joker, "label", None)
        or getattr(joker, "ability_name", None)
        or type(joker).__name__
    )
    return "".join(character for character in str(value).lower() if character.isalnum())


def _discard_conflict_indices(state: BalatroState, candidate: object) -> tuple[int, ...]:
    """Return owned slots mechanically incompatible with this candidate."""
    candidate_token = _joker_token(candidate)
    burnt = {"burnt", "burntjoker"}
    green = {"green", "greenjoker"}
    burglar = {"burglar", "burglarjoker"}
    discard_required = {
        "burnt",
        "burntjoker",
        "castle",
        "castlejoker",
        "faceless",
        "facelessjoker",
        "hittheroad",
        "hittheroadjoker",
        "mailinrebate",
        "mailinrebatejoker",
        "tradingcard",
        "tradingcardjoker",
        "yorick",
        "yorickjoker",
    }
    discard_capacity_payoffs = {
        "banner",
        "bannerjoker",
        "delayedgratification",
        "delayedgratificationjoker",
    }
    discard_capacity_sources = {
        "drunkard",
        "drunkardjoker",
        "merryandy",
        "merryandyjoker",
    }
    burglar_incompatible = (
        discard_required | discard_capacity_payoffs | discard_capacity_sources
    )

    if candidate_token in burglar:
        opposing = burglar_incompatible
    elif candidate_token in burglar_incompatible:
        opposing = burglar | (green if candidate_token in burnt else set())
    elif candidate_token in green:
        opposing = burnt
    else:
        return ()

    return tuple(
        index
        for index, joker in enumerate(getattr(state, "jokers", ()) or ())
        if _joker_token(joker) in opposing
    )


def _enforce_discard_resource_conflict(
    state: BalatroState,
    candidate: object,
    decision: JokerAcquisitionDecision,
) -> JokerAcquisitionDecision:
    """Apply the exact Burglar/discard-resource coexistence invariant."""
    conflict_indices = _discard_conflict_indices(state, candidate)
    if not conflict_indices:
        return decision
    if decision.action == REPLACE and getattr(decision, "selected", None) is not None:
        try:
            replace_index = int(decision.selected.replace_index)
        except (AttributeError, TypeError, ValueError):
            replace_index = -1
        if replace_index in conflict_indices:
            return replace(
                decision,
                rationale=(
                    *decision.rationale,
                    "discard-resource conflict resolved by replacing the opposing component",
                ),
            )
    return replace(
        decision,
        action=HOLD,
        selected=None,
        rationale=(
            *decision.rationale,
            "discard-resource conflict blocks coexistence: Burglar removes the activation/count window required by the candidate or incumbent",
            "future Bond potential cannot justify an owned Joker whose trigger, payout, or extra-discard benefit is currently impossible",
        ),
    )


def _conflict_set(composition) -> frozenset[frozenset[str]]:
    result: set[frozenset[str]] = set()
    for conflict in tuple(getattr(composition, "conflicts", ()) or ()):
        try:
            left, right = conflict
        except (TypeError, ValueError):
            continue
        result.add(frozenset((str(left), str(right))))
    return frozenset(result)


def _new_canonical_conflicts(
    state: BalatroState,
    candidate: object,
    *,
    replace_index: int | None,
) -> frozenset[frozenset[str]]:
    """Project the exact proposed roster change and return newly-created conflicts."""
    try:
        _, before_composition = evaluate_bond_composition(state)
        projected = copy.copy(state)
        projected.jokers = list(getattr(state, "jokers", ()) or ())
        if replace_index is None:
            projected.jokers.append(candidate)
        else:
            if replace_index < 0 or replace_index >= len(projected.jokers):
                return frozenset()
            projected.jokers[replace_index] = candidate
        _, after_composition = evaluate_bond_composition(projected)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return frozenset()
    return _conflict_set(after_composition) - _conflict_set(before_composition)


def _format_conflicts(conflicts: frozenset[frozenset[str]]) -> str:
    pairs = ["/".join(sorted(pair)) for pair in conflicts]
    return ", ".join(sorted(pairs))


class PlaybookJokerAcquisitionPolicy:
    """Resolve Red/White D2 thresholds and enforce mechanical/Bond compatibility."""

    def __init__(self, transition_planner: JokerBuildTransitionPlanner) -> None:
        self.transition_planner = transition_planner

    def decide(
        self,
        state: BalatroState,
        candidate: object,
    ) -> JokerAcquisitionDecision:
        try:
            playbook = default_balatro_playbooks().for_state(state)
        except BalatroPlaybookNotFound:
            thresholds = JokerAcquisitionThresholds()
        else:
            thresholds = JokerAcquisitionThresholds.from_mapping(
                playbook.thresholds_for("D2")
            )

        decision = JokerAcquisitionPolicy(
            thresholds,
            transition_planner=self.transition_planner,
        ).decide(state, candidate)

        # Canonical composition conflicts are hard admission constraints. The
        # candidate's positive Bond progress must never numerically overpower a new
        # incompatibility. For replacement decisions, evaluate the exact selected
        # replacement so a transition that removes the opposing component remains legal.
        if decision.action != HOLD:
            replace_index = None
            if decision.action == REPLACE and getattr(decision, "selected", None) is not None:
                try:
                    replace_index = int(decision.selected.replace_index)
                except (AttributeError, TypeError, ValueError):
                    replace_index = None
            new_conflicts = _new_canonical_conflicts(
                state,
                candidate,
                replace_index=replace_index,
            )
            if new_conflicts:
                return replace(
                    decision,
                    action=HOLD,
                    selected=None,
                    rationale=(
                        *decision.rationale,
                        "canonical Bond conflict veto: acquisition would create a new incompatible build direction",
                        f"new conflicts={_format_conflicts(new_conflicts)}",
                    ),
                )

        # Explicit trigger-window safety remains fail-closed when two individual
        # sources conflict even though their broad Bonds do not. In particular,
        # Burglar removes every discard, so a discard-triggered Joker is dormant
        # for as long as Burglar remains owned. Future Bond potential cannot award
        # value to an activation window the current roster has made impossible.
        return _enforce_discard_resource_conflict(state, candidate, decision)
