from __future__ import annotations

"""Build-Health decision integration for the Red/White calibration line.

This layer compares current public-state health against projected legal Joker
transitions. It does not add raw catalogue points. Existing replacement,
Negative-retention, Eternal, affordability and D2 legality guards remain upstream
and authoritative.
"""

from dataclasses import is_dataclass, replace
from types import SimpleNamespace

from games.balatro.actions import END_SHOP, REFRESH_SHOP, BalatroAction
from games.balatro.build_health_runtime import RuntimeBuildHealthEvaluator, projected_state_with_jokers
from games.balatro.joker_policy import BUY, HOLD, REPLACE
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.short_horizon_shop_planner import recommend_bounded_shop_bundle
from games.balatro.shop_arbiter import BuildAwareShopArbiter


_HEALTH = RuntimeBuildHealthEvaluator()
_EARLY_SURVIVAL_ADEQUACY = 75.0
_MATERIAL_HEALTH_DELTA = 5.0
_MATERIAL_SCALING_DELTA = 7.5
_MAX_SURVIVAL_SACRIFICE_FOR_SCALING = 2.0

_EARLY_SCORING_COMPONENTS = frozenset({
    "abstractjoker", "cleverjoker", "craftyjoker", "crazyjoker",
    "deviousjoker", "drolljoker", "evensteven", "fibonaccijoker",
    "halfjoker", "icecream", "jollyjoker", "madjoker", "misprint",
    "oddtoodds", "popcorn", "scholarjoker", "slyjoker", "wilyjoker",
    "zanyjoker",
})
_HAND_COMPONENTS = {
    "PAIR": frozenset({"halfjoker", "jollyjoker", "slyjoker", "theduojoker"}),
    "TWO_PAIR": frozenset({"cleverjoker", "madjoker", "sparetrousers", "squarejoker"}),
    "STRAIGHT": frozenset({"crazyjoker", "deviousjoker", "fourfingers", "runnerjoker", "shortcut", "theorderjoker"}),
    "FLUSH": frozenset({"craftyjoker", "drolljoker", "thetribejoker"}),
}


def _updated(value, **changes):
    if is_dataclass(value):
        return replace(value, **changes)
    data = dict(getattr(value, "__dict__", {}))
    data.update(changes)
    return SimpleNamespace(**data)


def _joker_token(joker: object) -> str:
    value = (
        getattr(joker, "name", None)
        or getattr(joker, "label", None)
        or getattr(joker, "ability_name", None)
        or type(joker).__name__
    )
    return "".join(character for character in str(value).lower() if character.isalnum())


def _stable_public_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, (str, int, float, bool)):
        return (type(value).__name__, enum_value)
    if isinstance(value, dict):
        return tuple(
            sorted((str(key), _stable_public_value(item)) for key, item in value.items())
        )
    if isinstance(value, (list, tuple, set, frozenset)):
        items = tuple(_stable_public_value(item) for item in value)
        if isinstance(value, (set, frozenset)):
            return tuple(sorted(items, key=repr))
        return items
    return (type(value).__name__,)


def _public_object_signature(item: object):
    values = []
    try:
        mapping = vars(item)
    except TypeError:
        mapping = {}
    for key, value in sorted(mapping.items()):
        if str(key).startswith("_") or callable(value):
            continue
        values.append((str(key), _stable_public_value(value)))
    return (type(item).__name__, tuple(values))


def _joker_progress_signature(joker: object):
    public = getattr(joker, "public_state", None)
    public_values = _stable_public_value(public) if public is not None else ()
    return (
        _joker_token(joker),
        _public_object_signature(joker),
        bool(getattr(joker, "eternal", False)),
        str(getattr(joker, "edition", "") or ""),
        public_values,
    )


def _card_signature(card: object):
    return (
        str(getattr(card, "rank", "") or ""),
        str(getattr(card, "suit", "") or ""),
        str(getattr(card, "enhancement", "") or ""),
        str(getattr(card, "seal", "") or ""),
        str(getattr(card, "edition", "") or ""),
        bool(getattr(card, "debuffed", False)),
        int(getattr(card, "permanent_bonus", 0) or 0),
    )


def _deck_signature(state):
    phase = str(getattr(state, "phase", "")).upper()
    deck = getattr(state, "owned_deck", None) if phase == "SHOP" else None
    if deck is None:
        deck = getattr(state, "deck", ()) or ()
    return tuple(sorted(_card_signature(card) for card in deck))


def _state_signature(state):
    levels = getattr(state, "hand_levels", {}) or {}
    play_counts = getattr(state, "hand_play_counts", {}) or {}
    round_counts = getattr(state, "round_hand_play_counts", {}) or {}
    return (
        max(1, int(getattr(state, "ante", 1) or 1)),
        int(getattr(state, "round", getattr(state, "round_num", 0)) or 0),
        str(getattr(state, "phase", "")),
        int(getattr(state, "money", 0) or 0),
        int(getattr(state, "score", 0) or 0),
        int(getattr(state, "blind_score", 0) or 0),
        int(getattr(state, "hands_remaining", 0) or 0),
        int(getattr(state, "discards_remaining", 0) or 0),
        int(getattr(state, "hand_size", 0) or 0),
        int(getattr(state, "joker_slots", 0) or 0),
        int(getattr(state, "consumable_slots", 0) or 0),
        str(getattr(state, "last_played_hand", "") or ""),
        str(getattr(state, "boss_name", "") or ""),
        bool(getattr(state, "boss_blind_state_observed", False)),
        tuple(sorted(str(value) for value in getattr(state, "boss_blind_hands", ()) or ())),
        str(getattr(state, "boss_blind_only_hand", "") or ""),
        tuple(_joker_progress_signature(joker) for joker in getattr(state, "jokers", ()) or ()),
        tuple(_public_object_signature(value) for value in getattr(state, "consumables", ()) or ()),
        tuple(_public_object_signature(value) for value in getattr(state, "vouchers", ()) or ()),
        tuple(sorted((str(key), int(value or 1)) for key, value in levels.items())),
        tuple(sorted((str(key), int(value or 0)) for key, value in play_counts.items())),
        tuple(sorted((str(key), int(value or 0)) for key, value in round_counts.items())),
        _deck_signature(state),
    )


def _cached_health(owner, state):
    signature = _state_signature(state)
    cached = getattr(owner, "_build_health_cache", None)
    if cached is not None and cached[0] == signature:
        return cached[1]
    health = _HEALTH.evaluate(state)
    owner._build_health_cache = (signature, health)
    return health


def _projected_health(state, jokers):
    projected = projected_state_with_jokers(state, jokers)
    return _HEALTH.evaluate(projected)


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


def _hand_count(state, hand: str) -> int:
    counts = getattr(state, "hand_play_counts", {}) or {}
    return max(
        0,
        int(counts.get(hand, counts.get(hand.replace("_", " ").title(), 0)) or 0),
    )


def _demonstrated_hand_component(state, candidate_token: str) -> str | None:
    counts = {hand: _hand_count(state, hand) for hand in _HAND_COMPONENTS}
    total = sum(
        max(0, int(value or 0))
        for value in (getattr(state, "hand_play_counts", {}) or {}).values()
    )
    for hand, components in _HAND_COMPONENTS.items():
        plays = counts[hand]
        if candidate_token not in components or plays < 3:
            continue
        if total <= 0 or plays / total >= 0.25 or plays == max(counts.values()):
            return hand
    return None


def _glass_retrigger_component(state, candidate_token: str) -> bool:
    if candidate_token != "hangingchadjoker":
        return False
    deck = getattr(state, "owned_deck", None)
    if deck is None:
        deck = getattr(state, "deck", ()) or ()
    return any(
        str(getattr(card, "enhancement", "") or "").lower() == "glass"
        for card in deck
    )


def _free_slot_engine_reason(state, candidate, decision, option) -> str | None:
    """Return a mechanical reason to admit an otherwise-held free-slot Joker."""
    token = _joker_token(candidate)
    ante = max(1, int(getattr(state, "ante", 1) or 1))
    money_after = _option_money_after(option)
    reserve = _reserve_target(decision)
    owned = tuple(getattr(state, "jokers", ()) or ())

    if token in _EARLY_SCORING_COMPONENTS and ante <= 2 and money_after >= 0:
        return "early scoring component fills an unfinished survival board"
    if token == "halfjoker" and ante <= 4 and money_after >= max(0, reserve - 3):
        return "Half Joker is immediate early Pair/High-Card engine power"
    if token == "goldenjoker" and ante <= 6 and money_after >= (0 if ante <= 2 else reserve):
        return "Golden Joker is profitable universal filler in a genuinely free slot"
    if token == "constellationjoker" and money_after >= max(10, reserve):
        return "Constellation supplies persistent Planet-fed scaling runway"

    hand = _demonstrated_hand_component(state, token)
    if hand is not None and money_after >= (0 if ante <= 2 else reserve):
        return f"candidate completes the demonstrated {hand} scoring direction"
    if _glass_retrigger_component(state, token) and money_after >= reserve:
        return "Hanging Chad retriggers existing Glass scoring cards"
    if not owned and token in _EARLY_SCORING_COMPONENTS and ante <= 3 and money_after >= 0:
        return "first scoring Joker is required before speculative support purchases"
    return None


def _health_aware_joker_decision(policy, state, candidate, decision):
    options = tuple(getattr(decision, "options", ()) or ())
    if not options:
        return decision
    current = _cached_health(policy, state)
    ante = max(1, int(getattr(state, "ante", 1) or 1))
    free_slot = len(getattr(state, "jokers", ()) or ()) < int(getattr(state, "joker_slots", 0) or 0)

    if free_slot:
        option = options[0]
        if not bool(getattr(option, "eligible", False)):
            return decision
        projected = _projected_health(state, _free_slot_projected_jokers(state, candidate))
        survival_gain = projected.survival - current.survival
        scaling_gain = projected.scaling - current.scaling
        early_survival_fix = (
            ante <= 2
            and current.survival < _EARLY_SURVIVAL_ADEQUACY
            and survival_gain >= _MATERIAL_HEALTH_DELTA
            and projected.immediate >= current.immediate
            and _option_money_after(option) >= 0
        )
        scaling_fix = (
            ante >= 3
            and current.scaling_deficit
            and (projected.scaling >= 50.0 or scaling_gain >= _MATERIAL_SCALING_DELTA)
            and projected.survival >= current.survival - _MAX_SURVIVAL_SACRIFICE_FOR_SCALING
            and _option_money_after(option) >= _reserve_target(decision)
        )
        engine_reason = _free_slot_engine_reason(state, candidate, decision, option)
        if decision.action == HOLD and (early_survival_fix or scaling_fix or engine_reason):
            reason = (
                engine_reason
                or ("early survival adequacy" if early_survival_fix else "midgame scaling adequacy")
            )
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
        projected = _projected_health(state, projected_jokers)
        scaling_gain = projected.scaling - current.scaling
        survival_loss = current.survival - projected.survival
        if scaling_gain < _MATERIAL_SCALING_DELTA and projected.scaling < 50.0:
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
    return _updated(
        result,
        action=recommendation.action,
        source="BUILD_HEALTH_BUNDLE",
        normalized_gain=max(0.001, float(getattr(result, "normalized_gain", 0.0))),
        rationale=(*recommendation.rationale, *getattr(result, "rationale", ())),
    )


def _health_reroll_decision(arbiter, state, result, reroll_cost):
    if str(getattr(result.action, "name", "")) != END_SHOP or reroll_cost is None:
        return result

    # D11 remains authoritative for reroll admission. Real production
    # ShopArbiterDecision objects carry the D11 recommendation even when END_SHOP
    # wins the parent comparison. Build Health must not manufacture a reroll after
    # D11 has already evaluated and rejected (or priced) that same action.
    if getattr(result, "reroll", None) is not None:
        return result

    try:
        cost = int(reroll_cost)
    except (TypeError, ValueError):
        return result
    if cost <= 0:
        return result

    health = _cached_health(arbiter, state)
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
    return _updated(
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
            result = original_shop_decide(self, state, visible_actions, reroll_cost=reroll_cost)
            result = _bundle_decision(state, result, self)
            return _health_reroll_decision(self, state, result, reroll_cost)

        BuildAwareShopArbiter.decide = shop_decide
        BuildAwareShopArbiter._build_health_policy_installed = True
