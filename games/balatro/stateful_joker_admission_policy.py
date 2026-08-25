from __future__ import annotations

"""Final D2 guards for stateful Joker purchases observed failing live.

These are mechanical admission constraints rather than catalogue tuning:
- Madness makes paid non-Eternal support/economy pieces disposable on future
  Small/Big blind selections, so only direct scoring purchases may coexist without
  an explicit protection mechanism;
- To Do List must not be bought for an exotic hand target with no demonstrated
  play/strategy path.
"""

from copy import copy
from dataclasses import replace
from typing import Mapping

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.build.joker_scenarios import ScenarioJokerBehaviorAnalyzer
from games.balatro.joker_policy import BUY, HOLD, REPLACE
from games.balatro.joker_edition import (
    joker_edition_universal_value,
    joker_has_negative_edition,
)
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy


_EXOTIC_HANDS = frozenset({
    "STRAIGHT_FLUSH",
    "FIVE_OF_A_KIND",
    "FLUSH_HOUSE",
    "FLUSH_FIVE",
})

_HAND_SUPERSETS = {
    "PAIR": frozenset({
        "PAIR", "TWO_PAIR", "THREE_OF_A_KIND", "FULL_HOUSE",
        "FOUR_OF_A_KIND", "FIVE_OF_A_KIND", "FLUSH_HOUSE", "FLUSH_FIVE",
    }),
    "TWO_PAIR": frozenset({"TWO_PAIR", "FULL_HOUSE", "FLUSH_HOUSE"}),
    "THREE_OF_A_KIND": frozenset({
        "THREE_OF_A_KIND", "FULL_HOUSE", "FOUR_OF_A_KIND",
        "FIVE_OF_A_KIND", "FLUSH_HOUSE", "FLUSH_FIVE",
    }),
    "STRAIGHT": frozenset({"STRAIGHT", "STRAIGHT_FLUSH"}),
    "FLUSH": frozenset({"FLUSH", "STRAIGHT_FLUSH", "FLUSH_HOUSE", "FLUSH_FIVE"}),
    "FULL_HOUSE": frozenset({"FULL_HOUSE", "FLUSH_HOUSE"}),
    "FOUR_OF_A_KIND": frozenset({"FOUR_OF_A_KIND", "FIVE_OF_A_KIND", "FLUSH_FIVE"}),
    "FIVE_OF_A_KIND": frozenset({"FIVE_OF_A_KIND", "FLUSH_FIVE"}),
}


def _token(value: object) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _joker_name(joker: object) -> str:
    return _token(
        getattr(joker, "name", None)
        or getattr(joker, "label", None)
        or getattr(joker, "ability_name", None)
        or joker.__class__.__name__
    )


def _hand_token(value: object) -> str:
    return "_".join(
        str(value or "").upper().replace("-", " ").replace("_", " ").split()
    )


def _candidate_hand_requirements(candidate: object) -> tuple[str, ...]:
    try:
        descriptor = ScenarioJokerBehaviorAnalyzer().describe(candidate)
    except (AttributeError, TypeError, ValueError):
        return ()
    return tuple(
        sorted(
            {
                _hand_token(str(feature).split(":", 1)[1])
                for feature in tuple(getattr(descriptor, "requires", ()) or ())
                if str(feature).lower().startswith("hand:")
            }
        )
    )


def _planned_hand_bonds(state) -> frozenset[str]:
    try:
        _, composition = evaluate_bond_composition(state)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return frozenset()
    values: set[str] = set()
    plan = getattr(composition, "strategy_plan", None)
    for goal in tuple(getattr(plan, "bond_goals", ()) or ()):
        values.add(str(getattr(goal, "bond_id", "") or ""))
    pinned = getattr(composition, "pinned_strategy_id", None)
    for candidate in tuple(getattr(composition, "strategy_candidates", ()) or ()):
        if str(getattr(candidate, "strategy_id", "") or "") == str(pinned or ""):
            values.update(str(value) for value in tuple(candidate.bond_ids or ()))
    return frozenset(values)


def _hand_requirements_supported(state, candidate: object) -> bool:
    """Require public evidence before opening a conditional hand-payoff axis."""
    requirements = _candidate_hand_requirements(candidate)
    if not requirements:
        return True

    bond_ids = {
        "HIGH_CARD": "high_card", "PAIR": "pair", "TWO_PAIR": "two_pair",
        "THREE_OF_A_KIND": "three_kind", "FOUR_OF_A_KIND": "four_kind",
        "STRAIGHT": "straight", "FLUSH": "flush", "FULL_HOUSE": "full_house",
        "STRAIGHT_FLUSH": "straight_flush", "FIVE_OF_A_KIND": "five_kind",
        "FLUSH_HOUSE": "flush_house", "FLUSH_FIVE": "flush_five",
    }
    planned = _planned_hand_bonds(state)
    if any(bond_ids.get(hand) in planned for hand in requirements):
        return True

    counts = {
        _hand_token(hand): max(0, int(value or 0))
        for hand, value in (getattr(state, "hand_play_counts", {}) or {}).items()
    }
    total = sum(counts.values())
    if total <= 0:
        return False
    for requirement in requirements:
        accepted = _HAND_SUPERSETS.get(requirement, frozenset({requirement}))
        plays = sum(counts.get(hand, 0) for hand in accepted)
        if plays >= 2 and plays / total >= 0.20:
            return True
    return False


def _creates_strategy(state, candidate, decision) -> bool:
    try:
        _, before = evaluate_bond_composition(state)
        projected = copy(state)
        projected.jokers = list(getattr(state, "jokers", ()) or ())
        if decision.action == REPLACE and getattr(decision, "selected", None) is not None:
            index = int(decision.selected.replace_index)
            projected.jokers[index] = candidate
        else:
            projected.jokers.append(candidate)
        _, after = evaluate_bond_composition(projected)
    except (AttributeError, IndexError, TypeError, ValueError, RuntimeError):
        return False
    before_best = max(
        (int(getattr(value, "commitment", 0)) for value in tuple(before.strategy_candidates or ())),
        default=0,
    )
    after_best = max(
        (int(getattr(value, "commitment", 0)) for value in tuple(after.strategy_candidates or ())),
        default=0,
    )
    return after_best > before_best and after_best >= 1


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


def _has_retriggerable_held_target(state) -> bool:
    deck = getattr(state, "owned_deck", None)
    if deck is None:
        deck = getattr(state, "deck", ()) or ()
    if any(
        str(getattr(card, "enhancement", "") or "").lower() in {"steel", "gold"}
        or str(getattr(card, "seal", "") or "").lower() in {"blue", "red"}
        for card in deck
    ):
        return True
    return any(
        _joker_name(joker) in {
            "baron", "baronjoker", "reservedparking", "reservedparkingjoker",
            "shootthemoon", "shootthemoonjoker",
        }
        for joker in tuple(getattr(state, "jokers", ()) or ())
    )


def _has_additive_scoring_base(state) -> bool:
    return any(
        _direct_scoring_candidate(joker)
        and _joker_name(joker) not in {"obelisk", "obeliskjoker"}
        for joker in tuple(getattr(state, "jokers", ()) or ())
    )


def install_stateful_joker_admission_policy() -> None:
    if getattr(PlaybookJokerAcquisitionPolicy, "_stateful_admission_installed", False):
        return
    original = PlaybookJokerAcquisitionPolicy.decide

    def decide(self, state, candidate):
        decision = original(self, state, candidate)
        name = _joker_name(candidate)
        if decision.action != HOLD and name in {"mime", "mimejoker"} and not _has_retriggerable_held_target(state):
            return replace(
                decision,
                action=HOLD,
                selected=None,
                rationale=(
                    *decision.rationale,
                    "Mime activation veto: no Steel/Gold/Blue/Red held-card effect or per-held-card Joker payoff exists",
                    "aggregate held-state Jokers such as Blackboard and Raised Fist are not Mime targets",
                ),
            )

        if (
            decision.action != HOLD
            and name in {"obelisk", "obeliskjoker"}
            and float(getattr(candidate, "x_mult", 1.0) or 1.0) <= 1.0
            and not _has_additive_scoring_base(state)
        ):
            return replace(
                decision,
                action=HOLD,
                selected=None,
                rationale=(
                    *decision.rationale,
                    "Obelisk activation veto: X1 scaler cannot be the board's first/only scoring Joker",
                    "secure additive Chips/Mult before buying a brittle multiplier engine",
                ),
            )

        if decision.action == HOLD:
            return decision

        if (
            tuple(getattr(state, "jokers", ()) or ())
            and getattr(candidate, "discovered", True) is not False
            and joker_edition_universal_value(candidate) <= 0.0
            and not _hand_requirements_supported(state, candidate)
            and not _creates_strategy(state, candidate, decision)
        ):
            requirements = ",".join(_candidate_hand_requirements(candidate))
            return replace(
                decision,
                action=HOLD,
                selected=None,
                rationale=(
                    *decision.rationale,
                    f"conditional hand-payoff veto: required hands={requirements} have no sustained public use or applied Strategy Plan",
                    "an isolated off-direction payoff does not open a new Bond axis after the first Joker",
                    "editions, collection-critical offers, and genuine strategy-forming transitions retain authority",
                ),
            )

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
