from __future__ import annotations

"""Exact Eye/Mouth D1 candidate constraints and subordinate Mouth evidence."""

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.hand_action_policy import HandActionDecision, PACE_RECOVERY


MOUTH_FORCED_STRUCTURE_FIT = 2.0
MOUTH_REDRAW_WIDTH_FIT = 0.10
MOUTH_STRUCTURE_EPSILON = 1e-12


def _hand_type(policy, state, plan) -> str:
    rules = hand_rules_for_state(state)
    return str(
        policy._hand_evaluator.evaluate(
            list(plan.action.cards),
            rules=rules,
        ).value
    ).upper()


def eye_filter(policy, state, plans):
    if str(getattr(state, "boss_name", "") or "") != "The Eye":
        return tuple(plans)
    if boss_blind_disabled_by_owned_jokers(state):
        return tuple(plans)

    supplied = tuple(plans)
    used = {
        str(value).upper()
        for value in (getattr(state, "boss_blind_hands", set()) or set())
    }
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


def mouth_locked_hand(state) -> str | None:
    if str(getattr(state, "boss_name", "") or "") != "The Mouth":
        return None
    if boss_blind_disabled_by_owned_jokers(state):
        return None
    value = getattr(state, "boss_blind_only_hand", None)
    return str(value).upper() if value else None


def mouth_retained_structure(policy, state, action, forced: str) -> float:
    removed = {id(card) for card in tuple(getattr(action, "cards", ()) or ())}
    kept = [
        card
        for card in tuple(getattr(state, "hand", ()) or ())
        if id(card) not in removed
    ]
    rules = hand_rules_for_state(state)
    try:
        return float(policy._structure_fit(kept, forced, rules=rules))
    except TypeError:
        return float(policy._structure_fit(kept, forced))


def mouth_zero_score_play_recovery(policy, state, plans, forced: str):
    supplied = tuple(plan for plan in plans if plan.action.name == PLAY_CARDS)
    if not supplied:
        return ()

    records = tuple(
        (
            plan,
            mouth_retained_structure(policy, state, plan.action, forced),
            len(tuple(getattr(plan.action, "cards", ()) or ())),
        )
        for plan in supplied
    )
    best_structure = max(structure for _, structure, _ in records)
    structure_equivalent = tuple(
        record
        for record in records
        if record[1] + MOUTH_STRUCTURE_EPSILON >= best_structure
    )
    best_width = max(width for _, _, width in structure_equivalent)
    return tuple(
        plan
        for plan, _, width in structure_equivalent
        if width == best_width
    )


def mouth_filter(policy, state, plans):
    supplied = tuple(plans)
    forced = mouth_locked_hand(state)
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

    if int(getattr(state, "discards_remaining", 0) or 0) <= 0:
        recovery = mouth_zero_score_play_recovery(policy, state, supplied, forced)
        if recovery:
            return recovery
    return supplied


def constrain_boss_hand_plans(policy, state, plans):
    return mouth_filter(policy, state, eye_filter(policy, state, plans))


def mouth_discard_fit(policy, state, action) -> tuple[float, tuple[str, ...]]:
    forced = mouth_locked_hand(state)
    if forced is None or action.name != DISCARD_CARDS:
        return 0.0, ()

    structure = mouth_retained_structure(policy, state, action, forced)
    redraw_width = len(tuple(getattr(action, "cards", ()) or ()))
    value = structure * MOUTH_FORCED_STRUCTURE_FIT + redraw_width * MOUTH_REDRAW_WIDTH_FIT
    return value, (
        f"The Mouth locked to {forced}: retained forced-hand structure={structure:.3f}",
        f"The Mouth redraw width={redraw_width}; forced-hand evidence={value:+.3f}",
        "Mouth redraw shaping is candidate evidence beneath canonical D1 survival ordering",
    )


def plan_clear_probability(plan) -> float:
    try:
        return float(getattr(plan.value, "clear_probability", 0.0) or 0.0)
    except (AttributeError, TypeError, ValueError):
        return 0.0


def mouth_discard_only_decision(
    policy,
    state,
    plans,
    *,
    search_attempts=(),
    setup_discard_consensus=False,
):
    forced = mouth_locked_hand(state)
    discards = tuple(plan for plan in plans if plan.action.name == DISCARD_CARDS)
    if forced is None or not discards:
        return None

    policy._ranking_state = state
    policy.build_evaluator.prepare(state)
    try:
        selected = max(
            discards,
            key=lambda plan: (
                *policy._within_type_key(plan),
                float(policy.evaluator.evaluate(state, plan.action)),
            ),
        )
        selected_value = float(policy.evaluator.evaluate(state, selected.action))
    finally:
        policy._ranking_state = None
        policy.build_evaluator.reset_cache()

    pace_target = float(policy._pace_target(state))
    return HandActionDecision(
        mode=PACE_RECOVERY,
        action=selected.action,
        selected_plan=selected,
        best_play=selected,
        best_discard=selected,
        thresholds=policy.thresholds,
        pace_target=pace_target,
        best_play_immediate_score=0.0,
        best_play_pace_ratio=0.0,
        selected_immediate_score=None,
        selected_pace_ratio=None,
        selected_fallback_value=selected_value,
        clear_path_candidates=0,
        sampled_clear_path_confirmed=False,
        setup_discard_consensus=bool(setup_discard_consensus),
        confidence=max(0.60, plan_clear_probability(selected)),
        rationale=(
            f"The Mouth is locked to {forced} and no matching PLAY_CARDS candidate is currently legal",
            "mechanics leave only DISCARD_CARDS, so D1 performs forced legal recovery instead of evaluating illegal Plays",
            "normal full-blind discard quality and Mouth retained-structure evidence rank the legal recovery candidates",
        ),
        candidate_count=len(tuple(plans)),
        plans=tuple(plans),
        search_attempts=tuple(search_attempts),
    )
