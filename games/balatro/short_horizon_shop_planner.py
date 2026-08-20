from __future__ import annotations

"""Bounded public-information multi-action shop planning.

The planner never executes a sequence in one step.  It chooses exactly one legal
SELL/BUY that belongs to a verified short-horizon plan, then the autonomous loop
must re-observe the shop and re-plan from authoritative state.
"""

from copy import deepcopy
from dataclasses import dataclass
from itertools import combinations, product

from games.balatro.actions import BUY_JOKER, SELL_JOKER, BalatroAction
from games.balatro.build_health_runtime import RuntimeBuildHealthEvaluator, projected_state_with_jokers
from games.balatro.joker_edition import joker_has_negative_edition
from games.balatro.strategy import GOLD, SILVER


_HEALTH = RuntimeBuildHealthEvaluator()
_MAX_BUNDLE_COMPONENTS = 2
_MAX_PRE_SALES = 2
_MAX_SURVIVAL_LOSS = 2.0
_MIN_SCALING_GAIN = 7.5


@dataclass(frozen=True)
class ShopBundleRecommendation:
    action: BalatroAction
    bundle_id: str
    projected_health: object
    rationale: tuple[str, ...]


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _canonical_joker(joker: object) -> str:
    token = _normalize(
        getattr(joker, "name", None)
        or getattr(joker, "label", None)
        or getattr(joker, "ability_name", None)
        or type(joker).__name__
    )
    if token.endswith("joker"):
        token = token[:-5]
    return token


def _price(joker: object) -> int:
    for key in ("price", "cost"):
        value = getattr(joker, key, None)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return max(0, int(value))
    return 0


def _sell_credit(joker: object) -> int:
    for key in ("sell_value", "sell_cost"):
        value = getattr(joker, key, None)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return max(0, int(value))
    return 0


def _tracker_from_arbiter(arbiter, state):
    try:
        policy = arbiter._joker_policy_for_state(state)
    except (AttributeError, TypeError, ValueError):
        return None
    planner = getattr(policy, "transition_planner", None)
    evaluator = getattr(planner, "evaluator", None)
    return getattr(evaluator, "strategy_tracker", None)


def _protected_indices(state, tracker) -> set[int]:
    jokers = tuple(getattr(state, "jokers", ()) or ())
    if tracker is not None:
        try:
            tracker = deepcopy(tracker)
        except (TypeError, ValueError):
            # Bundle planning must never mutate the live strategy tracker. If the
            # tracker cannot be isolated, fail closed and pre-sell nothing.
            return set(range(len(jokers)))

    protected: set[int] = set()
    for index, joker in enumerate(jokers):
        if bool(getattr(joker, "eternal", False)) or joker_has_negative_edition(joker):
            protected.add(index)
            continue
        if tracker is None:
            continue
        try:
            relation = tracker.evaluate_item(state, joker, kind="JOKER")
        except (AttributeError, KeyError, TypeError, ValueError):
            protected.add(index)
            continue
        if bool(getattr(relation, "active_alignment", False)) and getattr(relation, "tier", None) in {GOLD, SILVER}:
            protected.add(index)
    return protected


def _visible_offers(shop) -> dict[str, tuple[object, ...]]:
    grouped: dict[str, list[object]] = {}
    for joker in shop:
        grouped.setdefault(_canonical_joker(joker), []).append(joker)
    return {token: tuple(values) for token, values in grouped.items()}


def _bundle_specs(owned: set[str], visible) -> tuple[tuple[str, tuple[str, ...]], ...]:
    available = owned | set(visible)
    specs: list[tuple[str, tuple[str, ...]]] = []
    if {"bull", "bootstraps"} <= available:
        specs.append(("bull_bootstraps", ("bull", "bootstraps")))
    for scorer in ("hologram", "blue"):
        for generator in ("certificate", "marble"):
            if {scorer, generator} <= available:
                specs.append((f"deck_growth:{scorer}+{generator}", (scorer, generator)))
    return tuple(specs)


def _health_improves(current, projected) -> bool:
    survival_ok = projected.survival >= current.survival - _MAX_SURVIVAL_LOSS
    scaling_gain = projected.scaling - current.scaling
    fixes_deficit = current.scaling_deficit and projected.scaling >= 50.0
    material_growth = scaling_gain >= _MIN_SCALING_GAIN
    total_ok = projected.total >= current.total - 2.0
    return survival_ok and total_ok and (fixes_deficit or material_growth)


def _projection_tracker(tracker):
    if tracker is None:
        return None
    try:
        return deepcopy(tracker)
    except (TypeError, ValueError):
        return None


def _project(state, roster, money, tracker):
    projected = projected_state_with_jokers(state, roster)
    projected.money = max(0, int(money))
    return projected, _HEALTH.evaluate(
        projected,
        strategy_tracker=_projection_tracker(tracker),
    )


def recommend_bounded_shop_bundle(arbiter, state) -> ShopBundleRecommendation | None:
    jokers = tuple(getattr(state, "jokers", ()) or ())
    shop = tuple(getattr(state, "shop_jokers", ()) or ())
    if not shop:
        return None

    owned_by_token = {_canonical_joker(joker): joker for joker in jokers}
    visible_by_token = _visible_offers(shop)
    tracker = _tracker_from_arbiter(arbiter, state)
    current = _HEALTH.evaluate(state, strategy_tracker=tracker)
    slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
    free_slots = max(0, slots - len(jokers))
    money = max(0, int(getattr(state, "money", 0) or 0))
    ante = max(1, int(getattr(state, "ante", 1) or 1))
    reserve = 5 if ante <= 2 else 10
    protected = _protected_indices(state, tracker)
    replaceable = tuple(index for index in range(len(jokers)) if index not in protected)

    best = None
    for bundle_id, components in _bundle_specs(set(owned_by_token), visible_by_token):
        missing = tuple(token for token in components if token not in owned_by_token)
        if not missing or len(missing) > _MAX_BUNDLE_COMPONENTS:
            continue
        if any(token not in visible_by_token for token in missing):
            continue

        needed_sells = max(0, len(missing) - free_slots)
        if needed_sells > _MAX_PRE_SALES or needed_sells > len(replaceable):
            continue
        sell_sets = ((),) if needed_sells == 0 else combinations(replaceable, needed_sells)
        offer_sets = product(*(visible_by_token[token] for token in missing))

        # Materialize because sell-set iteration may need to compare every visible
        # edition/cost variant of the same semantic bundle component.
        offer_sets = tuple(tuple(values) for values in offer_sets)
        for sell_indices in sell_sets:
            sell_indices = tuple(sorted(sell_indices))
            remaining_roster = [
                joker for index, joker in enumerate(jokers) if index not in sell_indices
            ]
            for added in offer_sets:
                final_roster = tuple((*remaining_roster, *added))
                final_money = (
                    money
                    + sum(_sell_credit(jokers[index]) for index in sell_indices)
                    - sum(_price(joker) for joker in added)
                )
                if final_money < reserve:
                    continue

                projected_state, projected = _project(state, final_roster, final_money, tracker)
                if not _health_improves(current, projected):
                    continue

                score = (
                    projected.total,
                    projected.scaling,
                    projected.survival,
                    final_money,
                )
                candidate = (
                    score,
                    bundle_id,
                    missing,
                    added,
                    sell_indices,
                    final_money,
                    projected_state,
                    projected,
                )
                if best is None or candidate[0] > best[0]:
                    best = candidate

    if best is None:
        return None

    _, bundle_id, missing, added, sell_indices, final_money, _projected_state, projected = best

    if sell_indices:
        ranked_sales = []
        for index in sell_indices:
            interim_roster = tuple(
                joker for current_index, joker in enumerate(jokers) if current_index != index
            )
            interim_money = money + _sell_credit(jokers[index])
            _, interim_health = _project(state, interim_roster, interim_money, tracker)
            ranked_sales.append((interim_health.survival, interim_health.total, -index, index))
        index = max(ranked_sales)[-1]
        action = BalatroAction(SELL_JOKER, target=index)
        step = f"sell filler slot {index} first; re-observe before any purchase"
    else:
        ranked_buys = []
        for token, candidate in zip(missing, added):
            interim_roster = tuple((*jokers, candidate))
            interim_money = money - _price(candidate)
            _, interim_health = _project(state, interim_roster, interim_money, tracker)
            ranked_buys.append(
                (
                    interim_health.survival,
                    interim_health.scaling,
                    interim_health.total,
                    -_price(candidate),
                    token,
                    candidate,
                )
            )
        _, _, _, _, token, candidate = max(ranked_buys)
        action = BalatroAction(BUY_JOKER, target=candidate)
        step = f"buy {token} first; re-observe before complementary purchase"

    return ShopBundleRecommendation(
        action=action,
        bundle_id=bundle_id,
        projected_health=projected,
        rationale=(
            f"bounded shop bundle={bundle_id}",
            f"missing components={','.join(missing)}; planned pre-sales={sell_indices or 'none'}",
            f"projected final cash=${final_money}",
            f"Build Health {current.total:.1f}->{projected.total:.1f}; survival {current.survival:.1f}->{projected.survival:.1f}; scaling {current.scaling:.1f}->{projected.scaling:.1f}",
            step,
            "only one action is emitted; authoritative re-observation is mandatory before continuing the bundle",
        ),
    )
