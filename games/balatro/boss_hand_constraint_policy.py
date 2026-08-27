from __future__ import annotations

"""Hard public boss constraints and subordinate Mouth redraw evidence for D1.

The Eye cannot repeat poker-hand types during the current blind. The Mouth accepts
only its locked poker-hand type after the first scored hand. Those are exact public
mechanics and remain pre-arbitration candidate constraints.

When The Mouth is already locked, retained forced-hand structure and redraw width
are candidate evidence only. A legacy pure selector is retained for deterministic
regression compatibility, but production installation does not call it.
"""

from dataclasses import replace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.boss_trigger import boss_blind_disabled_by_owned_jokers
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.live.hand_action_policy import HandActionDecision, PACE_RECOVERY
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


MOUTH_FORCED_STRUCTURE_FIT = 2.0
MOUTH_REDRAW_WIDTH_FIT = 0.10


def _hand_type(policy, state, plan) -> str:
    rules = hand_rules_for_state(state)
    return str(
        policy._hand_evaluator.evaluate(
            list(plan.action.cards),
            rules=rules,
        ).value
    ).upper()


def _psychic_filter(state, plans):
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
    return supplied


def _mouth_discard_fit(policy, state, action) -> tuple[float, tuple[str, ...]]:
    forced = _mouth_locked_hand(state)
    if forced is None or action.name != DISCARD_CARDS:
        return 0.0, ()

    removed = {id(card) for card in getattr(action, "cards", ()) or ()}
    kept = [
        card
        for card in tuple(getattr(state, "hand", ()) or ())
        if id(card) not in removed
    ]
    rules = hand_rules_for_state(state)
    structure = float(policy._structure_fit(kept, forced, rules=rules))
    redraw_width = len(tuple(getattr(action, "cards", ()) or ()))
    value = structure * MOUTH_FORCED_STRUCTURE_FIT + redraw_width * MOUTH_REDRAW_WIDTH_FIT
    return value, (
        f"The Mouth locked to {forced}: retained forced-hand structure={structure:.3f}",
        f"The Mouth redraw width={redraw_width}; forced-hand evidence={value:+.3f}",
        "Mouth redraw shaping is candidate evidence beneath canonical D1 survival ordering",
    )


def _plan_clear_probability(plan) -> float:
    try:
        return float(getattr(plan.value, "clear_probability", 0.0) or 0.0)
    except (AttributeError, TypeError, ValueError):
        return 0.0


def _mouth_discard_only_decision(policy, state, plans, *, search_attempts=(), setup_discard_consensus=False):
    """Return the best legal recovery when Mouth mechanics eliminate every Play.

    This is not a Play-vs-Discard policy override: once The Mouth is locked and no
    matching poker hand exists, mechanics leave only DISCARD_CARDS as a legal D1
    action class. Keep illegal Plays out of the policy entirely and choose among the
    remaining legal discards using the normal production within-type ordering.
    """
    forced = _mouth_locked_hand(state)
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
        # No legal Play exists. Keep the non-optional legacy field populated with
        # the selected legal root plan; consumers must use action/selected_plan.
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
        confidence=max(0.60, _plan_clear_probability(selected)),
        rationale=(
            f"The Mouth is locked to {forced} and no matching PLAY_CARDS candidate is currently legal",
            "mechanics leave only DISCARD_CARDS, so D1 performs forced legal recovery instead of evaluating illegal Plays",
            "normal full-blind discard quality and Mouth retained-structure evidence rank the legal recovery candidates",
        ),
        candidate_count=len(tuple(plans)),
        plans=tuple(plans),
        search_attempts=tuple(search_attempts),
    )


def _mouth_forced_discard(policy, state, plans, decision):
    """Legacy pure selector retained only for deterministic compatibility tests."""
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
        try:
            return float(policy._structure_fit(kept, forced, rules=hand_rules_for_state(state)))
        except TypeError:
            return float(policy._structure_fit(kept, forced))

    current_plan = getattr(decision, "selected_plan", None)
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
        and _plan_clear_probability(plan) + tolerance + policy.EPSILON >= selected_probability
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
            "legacy compatibility helper only; production uses candidate evidence",
            *decision.rationale,
        ),
    )


def install_boss_hand_constraint_policy() -> None:
    if getattr(StrategyAwareLiveHandActionPolicy, "_boss_hand_constraints_installed", False):
        return

    original_decide = StrategyAwareLiveHandActionPolicy.decide
    original_strategy_fit = StrategyAwareLiveHandActionPolicy._strategy_fit

    def strategy_fit(self, state, action):
        base, rationale = original_strategy_fit(self, state, action)
        mouth_value, mouth_notes = _mouth_discard_fit(self, state, action)
        if mouth_value <= 0.0:
            return base, rationale
        return base + mouth_value, (*rationale, *mouth_notes)

    def decide(self, state, plans, **kwargs):
        constrained = _eye_filter(self, state, plans)
        constrained = _mouth_filter(self, state, constrained)
        if (
            constrained
            and not any(plan.action.name == PLAY_CARDS for plan in constrained)
            and any(plan.action.name == DISCARD_CARDS for plan in constrained)
        ):
            forced = _mouth_discard_only_decision(
                self,
                state,
                constrained,
                search_attempts=kwargs.get("search_attempts", ()),
                setup_discard_consensus=kwargs.get("setup_discard_consensus", False),
            )
            if forced is not None:
                return forced
        return original_decide(self, state, constrained, **kwargs)

    StrategyAwareLiveHandActionPolicy._strategy_fit = strategy_fit
    StrategyAwareLiveHandActionPolicy.decide = decide
    StrategyAwareLiveHandActionPolicy._boss_hand_constraints_installed = True
