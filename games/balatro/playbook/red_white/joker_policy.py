from __future__ import annotations

import copy
from dataclasses import replace

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro.build import JokerBuildTransitionPlanner
from games.balatro.joker_policy import (
    BUY,
    HOLD,
    REPLACE,
    JokerAcquisitionDecision,
    JokerAcquisitionPolicy,
    JokerAcquisitionThresholds,
)
from games.balatro.playbook import BalatroPlaybookNotFound, default_balatro_playbooks
from games.balatro.state import BalatroState


_STRATEGY_COMPLETION_WEIGHT = 2.0
_MISSING_COMPONENT_VALUE = 0.75
_MISSING_FEATURE_VALUE = 0.50
_PINNED_TRANSITION_VALUE = 1.25
_STRATEGY_COMPLETION_CAP = 3.0


def _joker_token(joker: object) -> str:
    value = (
        getattr(joker, "name", None)
        or getattr(joker, "label", None)
        or getattr(joker, "ability_name", None)
        or type(joker).__name__
    )
    return "".join(character for character in str(value).lower() if character.isalnum())


def _discard_conflict_indices(state: BalatroState, candidate: object) -> tuple[int, ...]:
    """Return owned slots mechanically incompatible with this candidate.

    Burnt needs the first discard. Green loses Mult on every discard; Burglar removes
    all discards. Green and Burglar are intentionally compatible with each other.
    """
    candidate_token = _joker_token(candidate)
    burnt = {"burnt", "burntjoker"}
    green = {"green", "greenjoker"}
    burglar = {"burglar", "burglarjoker"}

    if candidate_token in burnt:
        opposing = green | burglar
    elif candidate_token in green | burglar:
        opposing = burnt
    else:
        return ()

    return tuple(
        index
        for index, joker in enumerate(getattr(state, "jokers", ()) or ())
        if _joker_token(joker) in opposing
    )


def _projected_state(
    state: BalatroState,
    candidate: object,
    *,
    replace_index: int | None,
) -> BalatroState | None:
    projected = copy.copy(state)
    projected.jokers = list(getattr(state, "jokers", ()) or ())
    if replace_index is None:
        projected.jokers.append(candidate)
        return projected
    if replace_index < 0 or replace_index >= len(projected.jokers):
        return None
    projected.jokers[replace_index] = candidate
    return projected


def _strategy_completion_bonus(
    state: BalatroState,
    candidate: object,
    *,
    replace_index: int | None = None,
) -> tuple[float, tuple[str, ...]]:
    """Reward public one-Joker progress toward the strategy already being built.

    D2's canonical Bond projection rewards local Bond rank/progress changes, while
    FORMING retention prevents destructive replacement. Neither signal directly
    rewards filling the explicit missing components or missing semantic features of
    the current StrategyPlan. This term closes that gap without granting value to
    unrelated pivots: the projected plan must retain the same strategy id and
    improve its completion, missing-component count, missing-feature count, or
    commitment.
    """
    projected = _projected_state(
        state,
        candidate,
        replace_index=replace_index,
    )
    if projected is None:
        return 0.0, ()

    try:
        _, before_composition = evaluate_bond_composition(state)
        _, after_composition = evaluate_bond_composition(projected)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return 0.0, ()

    before = getattr(before_composition, "strategy_plan", None)
    after = getattr(after_composition, "strategy_plan", None)
    if before is None or after is None:
        return 0.0, ()

    strategy_id = str(getattr(before, "strategy_id", "") or "")
    if not strategy_id or str(getattr(after, "strategy_id", "") or "") != strategy_id:
        return 0.0, ()

    before_commitment = getattr(
        before,
        "commitment",
        StrategyCommitment.EXPLORATORY,
    )
    after_commitment = getattr(
        after,
        "commitment",
        StrategyCommitment.EXPLORATORY,
    )
    if before_commitment < StrategyCommitment.FORMING:
        return 0.0, ()

    before_completion = float(getattr(before, "completion", 0.0) or 0.0)
    after_completion = float(getattr(after, "completion", 0.0) or 0.0)
    completion_gain = max(0.0, after_completion - before_completion)

    before_missing = len(tuple(getattr(before, "missing_components", ()) or ()))
    after_missing = len(tuple(getattr(after, "missing_components", ()) or ()))
    components_filled = max(0, before_missing - after_missing)

    before_features = set(tuple(getattr(before, "missing_features", ()) or ()))
    after_features = set(tuple(getattr(after, "missing_features", ()) or ()))
    features_filled = len(before_features - after_features)

    pinned_transition = int(
        before_commitment < StrategyCommitment.PINNED
        and after_commitment >= StrategyCommitment.PINNED
    )
    if (
        completion_gain <= 0.0
        and components_filled <= 0
        and features_filled <= 0
        and not pinned_transition
    ):
        return 0.0, ()

    bonus = min(
        _STRATEGY_COMPLETION_CAP,
        _STRATEGY_COMPLETION_WEIGHT * completion_gain
        + _MISSING_COMPONENT_VALUE * min(2, components_filled)
        + _MISSING_FEATURE_VALUE * min(2, features_filled)
        + _PINNED_TRANSITION_VALUE * pinned_transition,
    )
    if bonus <= 0.0:
        return 0.0, ()

    return bonus, (
        f"same-strategy completion bonus={bonus:.3f} strategy={strategy_id}",
        f"strategy completion={before_completion:.3f}->{after_completion:.3f}",
        f"missing components={before_missing}->{after_missing}",
        f"missing features={len(before_features)}->{len(after_features)} resolved={features_filled}",
        f"commitment={before_commitment.name}->{after_commitment.name}",
    )


def _apply_strategy_completion_value(
    state: BalatroState,
    candidate: object,
    decision: JokerAcquisitionDecision,
) -> JokerAcquisitionDecision:
    if not decision.options:
        return decision

    changed = False
    rescored = []
    for option in decision.options:
        bonus, notes = _strategy_completion_bonus(
            state,
            candidate,
            replace_index=option.replace_index if option.mode == REPLACE else None,
        )
        if bonus <= 0.0:
            rescored.append(option)
            continue
        changed = True
        rescored.append(
            replace(
                option,
                build_gain=float(option.build_gain) + bonus,
                total_advantage=float(option.total_advantage) + bonus,
                rationale=(*option.rationale, *notes),
            )
        )

    if not changed:
        return decision

    ranked = tuple(
        sorted(
            rescored,
            key=lambda option: (
                -float(option.total_advantage),
                option.replace_index if option.replace_index is not None else -1,
            ),
        )
    )
    mode = ranked[0].mode
    if mode == BUY:
        best = ranked[0]
        action = (
            BUY
            if best.eligible
            and best.total_advantage > decision.thresholds.minimum_purchase_advantage
            else HOLD
        )
    else:
        eligible = [
            option
            for option in ranked
            if option.eligible
            and option.total_advantage
            > decision.thresholds.minimum_replacement_advantage
        ]
        best = eligible[0] if eligible else ranked[0]
        action = REPLACE if eligible else HOLD

    selected = best if action in {BUY, REPLACE} else None
    return replace(
        decision,
        action=action,
        selected=selected,
        options=ranked,
        rationale=(
            *decision.rationale,
            "D2 same-strategy completion value applied from canonical StrategyPlan projection",
            f"rescored best advantage={best.total_advantage:.3f}",
        ),
    )


class PlaybookJokerAcquisitionPolicy:
    """Resolve D2 thresholds per state while reusing one run-scoped B3 evaluator.

    The transition planner owns the shared build-value evaluator and its persistent
    playstyle-intent tracker. Only D2 thresholds are reconstructed from the active
    deck/stake playbook for each authoritative shop observation.
    """

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
        decision = _apply_strategy_completion_value(state, candidate, decision)

        # Pairwise mechanical safety is stronger than any current build preference.
        # A Burnt/Green/Burglar conflict may be resolved by a REPLACE that removes
        # the opposing Joker; it may never be admitted as a coexistence BUY or as a
        # replacement of some unrelated slot.
        conflict_indices = _discard_conflict_indices(state, candidate)
        if conflict_indices:
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
                            "discard-mechanic conflict resolved by replacing the opposing Burnt/Green/Burglar component",
                        ),
                    )
            return replace(
                decision,
                action=HOLD,
                selected=None,
                rationale=(
                    *decision.rationale,
                    "discard-mechanic conflict blocks coexistence: Burnt cannot share a build with Green Joker or Burglar",
                ),
            )

        return decision
