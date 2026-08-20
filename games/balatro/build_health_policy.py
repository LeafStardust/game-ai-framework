from __future__ import annotations

"""Build-Health decision integration for the Red/White calibration line.

This layer compares current public-state health against projected legal Joker
transitions.  It does not add raw catalogue points.  Existing committed-component,
Negative-retention, Eternal, affordability and D2 legality guards remain upstream
and authoritative.
"""

from dataclasses import is_dataclass, replace
from types import SimpleNamespace

from games.balatro.actions import END_SHOP, REFRESH_SHOP, BalatroAction
from games.balatro.build_health_runtime import (
    RuntimeBuildHealthEvaluator,
    projected_state_with_jokers,
)
from games.balatro.joker_policy import BUY, HOLD, REPLACE
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.short_horizon_shop_planner import recommend_bounded_shop_bundle
from games.balatro.shop_arbiter import BuildAwareShopArbiter


_HEALTH = RuntimeBuildHealthEvaluator()
_EARLY_SURVIVAL_ADEQUACY = 75.0
_MATERIAL_HEALTH_DELTA = 5.0
_MATERIAL_SCALING_DELTA = 7.5
_MAX_SURVIVAL_SACRIFICE_FOR_SCALING = 2.0


def _updated(value, **changes):
    if is_dataclass(value):
        return replace(value, **changes)
    data = dict(getattr(value, "__dict__", {}))
    data.update(changes)
    return SimpleNamespace(**data)


def _tracker_from_policy(policy):
    planner = getattr(policy, "transition_planner", None)
    evaluator = getattr(planner, "evaluator", None)
    return getattr(evaluator, "strategy_tracker", None)


def _joker_token(joker: object) -> str:
    value = (
        getattr(joker, "name", None)
        or getattr(joker, "label", None)
        or getattr(joker, "ability_name", None)
        or type(joker).__name__
    )
    return "".join(character for character in str(value).lower() if character.isalnum())


def _joker_progress_signature(joker: object):
    public = getattr(joker, "public_state", None)
    if isinstance(public, dict):
        public_values = tuple(sorted((str(k), repr(v)) for k, v in public.items()))
    else:
        public_values = ()
    return (
        _joker_token(joker),
        round(float(getattr(joker, "x_mult", 0.0) or 0.0), 4),
        round(float(getattr(joker, "mult", 0.0) or 0.0), 4),
        round(float(getattr(joker, "chips", 0.0) or 0.0), 4),
        bool(getattr(joker, "eternal", False)),
        str(getattr(joker, "edition", "") or ""),
        public_values,
    )


def _state_signature(state):
    levels = getattr(state, "hand_levels", {}) or {}
    return (
        max(1, int(getattr(state, "ante", 1) or 1)),
        str(getattr(state, "phase", "")),
        int(getattr(state, "money", 0) or 0),
        int(getattr(state, "blind_score", 0) or 0),
        int(getattr(state, "hands_remaining", 0) or 0),
        int(getattr(state, "discards_remaining", 0) or 0),
        tuple(_joker_progress_signature(joker) for joker in getattr(state, "jokers", ()) or ()),
        tuple(sorted((str(key), int(value or 1)) for key, value in levels.items())),
        len(getattr(state, "owned_deck", None) or getattr(state, "deck", ()) or ()),
    )


def _cached_health(owner, state, tracker):
    signature = _state_signature(state)
    cached = getattr(owner, "_build_health_cache", None)
    if cached is not None and cached[0] == signature:
        return cached[1]
    health = _HEALTH.evaluate(state, strategy_tracker=tracker)
    owner._build_health_cache = (signature, health)
    return health


def _projected_health(state, jokers, tracker):
    projected = projected_state_with_jokers(state, jokers)
    return _HEALTH.evaluate(projected, strategy_tracker=tracker)


def _health_notes(prefix: str, health) -> tuple[str, ...]:
    warnings = "; ".join(health.warnings) if health.warnings else "none"
    return (
        f"{prefix} Build Health={health.total:.1f}",
        f"{prefix} survival={health.survival:.1f} immediate={health.immediate:.1f} scaling={health.scaling:.1f} coherence={health.coherence:.1f} runway={health.runway:.1f}",
        f"{prefix} warnings={warnings}",
    )


def _free_slot_projected_jokers(state, candidate):
    return (*tuple(getattr(state, "jokers", ()) or ()), candidate)


def _replacement_projected_jokers(state, candidate, index: int):
    jokers = list(getattr(state, "jokers", ()) or ())
    if index < 0 or index >= len(jokers):
        return None
    jokers[index] = candidate
    return tuple(jokers)


def _option_money_after(option) -> int:
    economics = getattr(option, "economics", None)
    try:
        return int(getattr(economics, "money_after", -10**9))
    except (TypeError, ValueError):
        return -10**9


def _reserve_target(decision) -> int:
    try:
        return max(0, int(getattr(decision.thresholds, "reserve_target", 5) or 0))
    except (AttributeError, TypeError, ValueError):
        return 5


def _health_aware_joker_decision(policy, state, candidate, decision):
    options = tuple(getattr(decision, "options", ()) or ())
    if not options:
        return decision
    tracker = _tracker_from_policy(policy)
    current = _cached_health(policy, state, tracker)
    ante = max(1, int(getattr(state, "ante", 1) or 1))
    free_slot = len(getattr(state, "jokers", ()) or ()) < int(getattr(state, "joker_slots", 0) or 0)

    if free_slot:
        option = options[0]
        if not bool(getattr(option, "eligible", False)):
            return decision
        projected = _projected_health(
            state,
            _free_slot_projected_jokers(state, candidate),
            tracker,
        )
        survival_gain = projected.survival - current.survival
        scaling_gain = projected.scaling - current.scaling

        # Foundation survival: if the board is still inadequate, a purchase that
        # measurably improves the modeled next-blind survival state may override a
        # HOLD.  This is stronger than the former "positive scorer" rule because a
        # token +chips contribution that leaves survival unchanged does not qualify.
        early_survival_fix = (
            ante <= 2
            and current.survival < _EARLY_SURVIVAL_ADEQUACY
            and survival_gain >= _MATERIAL_HEALTH_DELTA
            and projected.immediate >= current.immediate
            and _option_money_after(option) >= 0
        )

        # Convergence scaling: preserve the normal reserve and never pay for future
        # growth by materially reducing current survival.  Crossing the scaling
        # adequacy floor is preferred, but a clearly measurable delta also counts.
        scaling_fix = (
            ante >= 3
            and current.scaling_deficit
            and (
                projected.scaling >= 50.0
                or scaling_gain >= _MATERIAL_SCALING_DELTA
            )
            and projected.survival
            >= current.survival - _MAX_SURVIVAL_SACRIFICE_FOR_SCALING
            and _option_money_after(option) >= _reserve_target(decision)
        )

        if decision.action == HOLD and (early_survival_fix or scaling_fix):
            reason = "early survival adequacy" if early_survival_fix else "midgame scaling adequacy"
            selected = _updated(
                option,
                rationale=(
                    *getattr(option, "rationale", ()),
                    f"Build Health transition admitted for {reason}",
                    f"survival delta={survival_gain:+.1f}; scaling delta={scaling_gain:+.1f}",
                ),
            )
            return _updated(
                decision,
                action=BUY,
                selected=selected,
                rationale=(
                    *getattr(decision, "rationale", ()),
                    f"Build Health overrides HOLD: {reason} materially improves without violating its safety guard",
                    *_health_notes("before", current),
                    *_health_notes("after", projected),
                ),
            )
        return decision

    # Full-roster health replacement.  Existing option.eligible already contains
    # Negative/Eternal/committed-build protection.  Health may only select among
    # those legal alternatives and only when the transaction remains net-positive.
    if not current.scaling_deficit:
        return decision

    candidates = []
    for option in options:
        if not bool(getattr(option, "eligible", False)):
            continue
        try:
            index = int(option.replace_index)
        except (AttributeError, TypeError, ValueError):
            continue
        projected_jokers = _replacement_projected_jokers(state, candidate, index)
        if projected_jokers is None:
            continue
        projected = _projected_health(state, projected_jokers, tracker)
        scaling_gain = projected.scaling - current.scaling
        survival_loss = current.survival - projected.survival
        if (
            scaling_gain < _MATERIAL_SCALING_DELTA
            and projected.scaling < 50.0
        ):
            continue
        if survival_loss > _MAX_SURVIVAL_SACRIFICE_FOR_SCALING:
            continue
        if float(getattr(option, "total_advantage", 0.0) or 0.0) <= 0.0:
            continue
        if _option_money_after(option) < _reserve_target(decision):
            continue
        candidates.append((projected.scaling, projected.survival, float(option.total_advantage), option, projected))

    if not candidates:
        return decision

    _, _, _, option, projected = max(candidates, key=lambda item: item[:3])
    if decision.action == REPLACE and getattr(decision, "selected", None) is option:
        return decision
    return _updated(
        decision,
        action=REPLACE,
        selected=option,
        rationale=(
            *getattr(decision, "rationale", ()),
            "Build Health selected a legal filler/support replacement because the current board has a scaling deficit",
            *_health_notes("before", current),
            *_health_notes("after", projected),
        ),
    )


def _shop_signature(state):
    return (
        max(1, int(getattr(state, "ante", 1) or 1)),
        int(getattr(state, "round", getattr(state, "round_num", 0)) or 0),
    )


def _bundle_decision(state, result, arbiter):
    if str(getattr(result.action, "name", "")) not in {END_SHOP, REFRESH_SHOP}:
        return result
    recommendation = recommend_bounded_shop_bundle(arbiter, state)
    if recommendation is None:
        return result
    return replace(
        result,
        action=recommendation.action,
        source="BUILD_HEALTH_BUNDLE",
        normalized_gain=max(0.001, float(getattr(result, "normalized_gain", 0.0))),
        rationale=(
            *recommendation.rationale,
            *getattr(result, "rationale", ()),
        ),
    )


def _health_reroll_decision(arbiter, state, result, reroll_cost):
    if str(getattr(result.action, "name", "")) != END_SHOP or reroll_cost is None:
        return result
    try:
        cost = int(reroll_cost)
    except (TypeError, ValueError):
        return result
    if cost <= 0:
        return result

    policy = arbiter._joker_policy_for_state(state)
    tracker = _tracker_from_policy(policy)
    health = _cached_health(arbiter, state, tracker)
    ante = max(1, int(getattr(state, "ante", 1) or 1))
    money = max(0, int(getattr(state, "money", 0) or 0))
    remaining = money - cost

    early_survival_search = (
        ante <= 2
        and health.survival < _EARLY_SURVIVAL_ADEQUACY
        and cost <= 5
        and remaining >= 2
    )
    scaling_search = (
        ante >= 3
        and health.scaling_deficit
        and cost <= 8
        and remaining >= 15
    )
    if not (early_survival_search or scaling_search):
        return result

    signature = _shop_signature(state)
    if getattr(arbiter, "_build_health_reroll_signature", None) == signature:
        return result
    arbiter._build_health_reroll_signature = signature
    reason = "survival inadequacy" if early_survival_search else "scaling deficit"
    return replace(
        result,
        action=BalatroAction(REFRESH_SHOP),
        source="BUILD_HEALTH_REROLL",
        normalized_gain=max(0.001, float(getattr(result, "normalized_gain", 0.0))),
        rationale=(
            f"Build Health bounded search: {reason} remains unresolved after visible shop choices",
            f"reroll=${cost}; cash after=${remaining}; one Build-Health reroll allowed for this shop checkpoint",
            *_health_notes("current", health),
            *getattr(result, "rationale", ()),
        ),
    )


def install_build_health_policy() -> None:
    if not getattr(PlaybookJokerAcquisitionPolicy, "_build_health_policy_installed", False):
        original_decide = PlaybookJokerAcquisitionPolicy.decide

        def decide(self, state, candidate):
            decision = original_decide(self, state, candidate)
            return _health_aware_joker_decision(self, state, candidate, decision)

        PlaybookJokerAcquisitionPolicy.decide = decide
        PlaybookJokerAcquisitionPolicy._build_health_policy_installed = True

    if not getattr(BuildAwareShopArbiter, "_build_health_policy_installed", False):
        original_shop_decide = BuildAwareShopArbiter.decide

        def shop_decide(self, state, visible_actions, *, reroll_cost: int | None):
            result = original_shop_decide(
                self,
                state,
                visible_actions,
                reroll_cost=reroll_cost,
            )
            result = _bundle_decision(state, result, self)
            return _health_reroll_decision(self, state, result, reroll_cost)

        BuildAwareShopArbiter.decide = shop_decide
        BuildAwareShopArbiter._build_health_policy_installed = True
