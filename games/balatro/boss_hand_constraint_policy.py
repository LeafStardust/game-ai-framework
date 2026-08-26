from __future__ import annotations

"""Hard public boss constraints for D1 hand admission.

The Eye cannot repeat poker-hand types during the current blind. That restriction is
safe to enforce before strategy-aware ranking when an unused legal type exists.

The Psychic is deliberately not filtered here: Balatro accepts plays containing fewer
than five cards; such a hand simply does not score. Those plays can still be useful as
deliberate hand-burning/milling actions, so legality and score semantics must remain
separate.
"""

from dataclasses import replace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.hand_action_policy import PACE_RECOVERY
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


def _hand_type(policy, state, plan) -> str:
    rules = hand_rules_for_state(state)
    return str(
        policy._hand_evaluator.evaluate(
            list(plan.action.cards),
            rules=rules,
        ).value
    ).upper()


def _psychic_filter(state, plans):
    """Compatibility no-op: Psychic short plays are legal actions in Balatro."""
    return tuple(plans)


def _eye_filter(policy, state, plans):
    if str(getattr(state, "boss_name", "") or "") != "The Eye":
        return tuple(plans)
    if boss_blind_disabled_by_owned_jokers(state):
        return tuple(plans)

    supplied = tuple(plans)
    used = {
        str(value).upper()
        for value in (getattr(state, "boss_blind_hands", set()) or set())
    }
    # Fall back to the public current-round counters when the blind-owned table was
    # not observed. Do not use lifetime run counts.
    if not used and not bool(getattr(state, "boss_blind_state_observed", False)):
        used = {
            str(hand).upper()
            for hand, count in (getattr(state, "round_hand_play_counts", {}) or {}).items()
            if int(count or 0) > 0
        }

    if not used:
        return supplied

    unused_plays = tuple(
        plan
        for plan in supplied
        if plan.action.name == PLAY_CARDS and _hand_type(policy, state, plan) not in used
    )
    if not unused_plays:
        return supplied
    discards = tuple(plan for plan in supplied if plan.action.name == DISCARD_CARDS)
    return (*unused_plays, *discards)


def _mouth_locked_hand(state) -> str | None:
    if str(getattr(state, "boss_name", "") or "") != "The Mouth":
        return None
    if boss_blind_disabled_by_owned_jokers(state):
        return None
    value = getattr(state, "boss_blind_only_hand", None)
    return str(value).upper() if value else None


def _mouth_filter(policy, state, plans):
    """Remove zero-score Mouth plays while a legal recovery line exists."""
    supplied = tuple(plans)
    forced = _mouth_locked_hand(state)
    if forced is None:
        return supplied

    matching = tuple(
        plan
        for plan in supplied
        if plan.action.name == PLAY_CARDS and _hand_type(policy, state, plan) == forced
    )
    discards = tuple(plan for plan in supplied if plan.action.name == DISCARD_CARDS)
    if matching or discards:
        return (*matching, *discards)
    # With no matching play and no discard, Balatro still requires a legal hand
    # burn. Preserve the original plans so D1 can advance to the terminal state.
    return supplied


def _plan_clear_probability(plan) -> float:
    try:
        return float(getattr(plan.value, "clear_probability", 0.0) or 0.0)
    except (AttributeError, TypeError, ValueError):
        return 0.0


def _mouth_forced_discard(policy, state, plans, decision):
    """Shape a Mouth redraw exclusively toward its already locked hand type.

    Generic Bond fit is irrelevant once the boss accepts only one poker hand. For
    survival-equivalent lines with equal retained forced-hand structure, drawing more
    cards strictly exposes more chances to find the missing ranks/suit, so prefer the
    widest such discard.
    """
    forced = _mouth_locked_hand(state)
    if forced is None or decision.action.name != DISCARD_CARDS:
        return decision

    discards = tuple(plan for plan in plans if plan.action.name == DISCARD_CARDS)
    if not discards:
        return decision

    def structure(plan) -> float:
        removed = {id(card) for card in plan.action.cards}
        kept = [
            card
            for card in tuple(getattr(state, "hand", ()) or ())
            if id(card) not in removed
        ]
        return float(policy._structure_fit(kept, forced))

    current_plan = getattr(decision, "selected_plan", None)
    if current_plan is None:
        current_plan = next(
            (
                plan
                for plan in discards
                if plan.action.cards == getattr(decision.action, "cards", None)
            ),
            None,
        )
    if current_plan is None:
        return decision

    selected_structure = structure(current_plan)
    selected_probability = _plan_clear_probability(current_plan)
    tolerance = float(
        getattr(
            getattr(decision, "thresholds", None),
            "safe_clear_probability_tolerance",
            0.0,
        )
        or 0.0
    )
    equivalent = tuple(
        plan
        for plan in discards
        if structure(plan) + policy.EPSILON >= selected_structure
        and _plan_clear_probability(plan) + tolerance + policy.EPSILON
        >= selected_probability
    )
    if not equivalent:
        return decision

    selected = max(
        equivalent,
        key=lambda plan: (
            _plan_clear_probability(plan),
            structure(plan),
            len(tuple(getattr(plan.action, "cards", ()) or ())),
            float(policy.evaluator.evaluate(state, plan.action)),
            policy._within_type_key(plan),
        ),
    )
    if selected.action.cards == decision.action.cards:
        return decision
    value = float(policy.evaluator.evaluate(state, selected.action))
    return replace(
        decision,
        mode=PACE_RECOVERY,
        action=selected.action,
        selected_plan=selected,
        selected_immediate_score=None,
        selected_pace_ratio=None,
        selected_fallback_value=value,
        confidence=max(float(getattr(decision, "confidence", 0.0) or 0.0), _plan_clear_probability(selected)),
        rationale=(
            f"The Mouth is locked to {forced}; forced-hand feasibility overrides unrelated Bond targets",
            f"retained {forced} structure={structure(selected):.3f}; redraw width={len(selected.action.cards)}",
            f"redraw clear probability={_plan_clear_probability(selected):.3f}; baseline={selected_probability:.3f}; tolerance={tolerance:.3f}",
            "forced-hand redraw shaping remains subordinate to D1 survival",
            *decision.rationale,
        ),
    )


def install_boss_hand_constraint_policy() -> None:
    if getattr(StrategyAwareLiveHandActionPolicy, "_boss_hand_constraints_installed", False):
        return

    original_decide = StrategyAwareLiveHandActionPolicy.decide

    def decide(self, state, plans, **kwargs):
        constrained = _eye_filter(self, state, plans)
        constrained = _mouth_filter(self, state, constrained)
        decision = original_decide(self, state, constrained, **kwargs)
        return _mouth_forced_discard(self, state, constrained, decision)

    StrategyAwareLiveHandActionPolicy.decide = decide
    StrategyAwareLiveHandActionPolicy._boss_hand_constraints_installed = True
