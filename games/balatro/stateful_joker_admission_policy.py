from __future__ import annotations

"""Final D2 guards for stateful Joker purchases observed failing live.

These are mechanical admission constraints rather than catalogue tuning:
- Madness makes paid non-Eternal support/economy pieces disposable on future
  Small/Big blind selections, so only direct scoring purchases may coexist without
  an explicit protection mechanism;
- To Do List must not be bought for an exotic hand target with no demonstrated
  play/strategy path.
"""

from dataclasses import replace
from typing import Mapping

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.build.joker_scenarios import ScenarioJokerBehaviorAnalyzer
from games.balatro.joker_policy import BUY, HOLD, REPLACE
from games.balatro.joker_edition import joker_has_negative_edition
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy


_EXOTIC_HANDS = frozenset({
    "STRAIGHT_FLUSH",
    "FIVE_OF_A_KIND",
    "FLUSH_HOUSE",
    "FLUSH_FIVE",
})


def _token(value: object) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _joker_name(joker: object) -> str:
    return _token(
        getattr(joker, "name", None)
        or getattr(joker, "label", None)
        or getattr(joker, "ability_name", None)
        or joker.__class__.__name__
    )


def _has_madness(state) -> bool:
    return any(
        _joker_name(joker) in {"madness", "madnessjoker"}
        for joker in tuple(getattr(state, "jokers", ()) or ())
    )


def _eternal(candidate: object) -> bool:
    return bool(getattr(candidate, "eternal", False))


def _direct_scoring_candidate(candidate: object) -> bool:
    try:
        descriptor = ScenarioJokerBehaviorAnalyzer().describe(candidate)
    except (AttributeError, TypeError, ValueError):
        descriptor = None
    if descriptor is None:
        return False
    outputs = {
        str(value).lower().replace("_", "")
        for value in set(descriptor.produces) | set(descriptor.transforms)
    }
    return any(
        any(marker in output for marker in ("chips", "mult", "xmult", "score"))
        for output in outputs
    )


def _target_hand(candidate: object) -> str:
    values = [
        getattr(candidate, "target_hand", None),
        getattr(candidate, "current_hand", None),
    ]
    public = getattr(candidate, "public_state", None)
    if isinstance(public, Mapping):
        values.extend((public.get("target_hand"), public.get("current_hand")))
    for value in values:
        if value:
            return "_".join(str(value).upper().replace("-", " ").replace("_", " ").split())
    return ""


def _plan_owns_hand(state, hand: str) -> bool:
    bond_id = {
        "STRAIGHT_FLUSH": "straight_flush",
        "FIVE_OF_A_KIND": "five_kind",
        "FLUSH_HOUSE": "flush_house",
        "FLUSH_FIVE": "flush_five",
    }.get(hand)
    if not bond_id:
        return False
    try:
        _, composition = evaluate_bond_composition(state)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return False
    if not getattr(composition, "pinned_strategy_id", None):
        return False
    plan = getattr(composition, "strategy_plan", None)
    if plan is None:
        return False
    return any(
        str(getattr(goal, "bond_id", "")) == bond_id
        for goal in tuple(getattr(plan, "bond_goals", ()) or ())
    )


def _todo_target_supported(state, candidate: object) -> bool:
    target = _target_hand(candidate)
    if not target or target not in _EXOTIC_HANDS:
        return True
    plays = getattr(state, "hand_play_counts", {}) or {}
    if int(plays.get(target, 0) or 0) > 0:
        return True
    return _plan_owns_hand(state, target)


def _projected_stencil_multiplier(state, candidate, decision) -> int | None:
    """Return Joker Stencil's exact multiplier after the proposed transaction."""
    if _joker_name(candidate) != "jokerstencil":
        return None

    jokers = list(getattr(state, "jokers", ()) or ())
    if decision.action == BUY:
        jokers.append(candidate)
    elif decision.action == REPLACE and getattr(decision, "selected", None) is not None:
        try:
            index = int(decision.selected.replace_index)
        except (AttributeError, TypeError, ValueError):
            return None
        if index < 0 or index >= len(jokers):
            return None
        jokers[index] = candidate
    else:
        return None

    slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
    ordinary = sum(
        _joker_name(joker) != "jokerstencil"
        and not joker_has_negative_edition(joker)
        for joker in jokers
    )
    return max(slots - ordinary, 1)


def install_stateful_joker_admission_policy() -> None:
    if getattr(PlaybookJokerAcquisitionPolicy, "_stateful_admission_installed", False):
        return
    original = PlaybookJokerAcquisitionPolicy.decide

    def decide(self, state, candidate):
        decision = original(self, state, candidate)
        if decision.action == HOLD:
            return decision

        name = _joker_name(candidate)
        if (
            _has_madness(state)
            and name not in {"madness", "madnessjoker"}
            and not _eternal(candidate)
            and not _direct_scoring_candidate(candidate)
        ):
            return replace(
                decision,
                action=HOLD,
                selected=None,
                rationale=(
                    *decision.rationale,
                    "Madness coexistence veto: non-Eternal purchase has no direct scoring output and is exposed to future destruction",
                    "do not pay for disposable support/economy pieces unless protection or immediate scoring justifies coexistence",
                ),
            )

        if name in {"todolist", "todolistjoker"} and not _todo_target_supported(state, candidate):
            target = _target_hand(candidate) or "UNKNOWN"
            return replace(
                decision,
                action=HOLD,
                selected=None,
                rationale=(
                    *decision.rationale,
                    f"To Do List target veto: {target} has no demonstrated exotic-hand path",
                    "stateful target value must be supported by actual play history or the pinned Strategy Plan",
                ),
            )

        stencil_multiplier = _projected_stencil_multiplier(state, candidate, decision)
        if stencil_multiplier is not None and stencil_multiplier <= 1:
            return replace(
                decision,
                action=HOLD,
                selected=None,
                rationale=(
                    *decision.rationale,
                    "Joker Stencil stateful veto: projected full roster leaves it at X1 Mult",
                    "isolated intrinsic XMult probes cannot override the exact post-transaction slot count",
                ),
            )

        return decision

    PlaybookJokerAcquisitionPolicy.decide = decide
    PlaybookJokerAcquisitionPolicy._stateful_admission_installed = True
