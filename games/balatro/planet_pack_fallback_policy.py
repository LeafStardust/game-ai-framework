from __future__ import annotations

"""Final Planet selection and acquisition discipline.

Opened Celestial packs should almost always yield a Planet: once the pack cost is
sunk, every offered Planet is a permanent scoring upgrade. Rank the complete Planet
pool by canonical strategy direction, realized hand development, practical hand
realisability, and only then generic card value.

Acquisition remains a separate resource decision. Celestial packs require actual
hand-development headroom and obey a diminishing global Planet-investment budget;
loose Planet acquisition is owned by D4 canonical projected StrategyDelta; loose
Tarots require stronger transaction value unless immediately usable. Arcana pack
acquisition is not changed here.

An active Planet-use scaler is a stronger mechanical authority than ordinary hand-
development headroom: every Planet is direct permanent engine progress. Reserve
protection remains authoritative.
"""

from collections import Counter
from copy import deepcopy
from dataclasses import replace
from itertools import combinations, combinations_with_replacement
from math import comb, factorial

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.planet_scaler_authority import has_planet_use_scaler
from games.balatro.planets import PLANET_CARDS, create_planet, eligible_planet_names
from games.balatro.shop_booster_policy import HOLD, BuildAwareShopBoosterPolicy
from games.balatro.shop_consumable_policy import (
    BUY,
    BUY_AND_USE,
    ConsumableAcquisitionDecision,
    ConsumableAcquisitionPolicy,
)


_PRACTICAL_HAND_PRIORITY = {
    "HIGH_CARD": 12,
    "PAIR": 11,
    "TWO_PAIR": 10,
    "THREE_OF_A_KIND": 9,
    "FLUSH": 8,
    "STRAIGHT": 7,
    "FULL_HOUSE": 6,
    "FOUR_OF_A_KIND": 5,
    "STRAIGHT_FLUSH": 4,
    "FIVE_OF_A_KIND": 3,
    "FLUSH_HOUSE": 2,
    "FLUSH_FIVE": 1,
}


def _token(value: object) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def _hand_token(value: object) -> str:
    return str(value or "").upper().replace(" ", "_")


def _planet_for_action(action):
    choice = getattr(action, "target", None)
    if choice is None or str(getattr(choice, "kind", "") or "").upper() != "PLANET":
        return None
    label = _token(getattr(choice, "label", ""))
    for planet in PLANET_CARDS.values():
        if _token(planet.name) == label:
            return planet
    return None


def _plan_hand_goals(state) -> set[str]:
    try:
        _, composition = evaluate_bond_composition(state)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return set()
    plan = getattr(composition, "strategy_plan", None)
    if plan is None or getattr(plan, "commitment", StrategyCommitment.EXPLORATORY) < StrategyCommitment.PINNED:
        return set()
    aliases = {
        "high_card": "HIGH_CARD",
        "pair": "PAIR",
        "two_pair": "TWO_PAIR",
        "three_kind": "THREE_OF_A_KIND",
        "four_kind": "FOUR_OF_A_KIND",
        "straight": "STRAIGHT",
        "flush": "FLUSH",
        "full_house": "FULL_HOUSE",
        "straight_flush": "STRAIGHT_FLUSH",
        "five_kind": "FIVE_OF_A_KIND",
        "flush_house": "FLUSH_HOUSE",
        "flush_five": "FLUSH_FIVE",
    }
    result: set[str] = set()
    for goal in tuple(getattr(plan, "bond_goals", ()) or ()):
        hand = aliases.get(str(getattr(goal, "bond_id", "")))
        if hand:
            result.add(hand)
    return result


def _hand_level(state, hand: str) -> int:
    levels = getattr(state, "hand_levels", {}) or {}
    return int(levels.get(hand, levels.get(hand.replace("_", " "), 1)) or 1)


def _hand_plays(state, hand: str) -> int:
    plays = getattr(state, "hand_play_counts", {}) or {}
    return int(plays.get(hand, plays.get(hand.replace("_", " "), 0)) or 0)


def _normalized_play_counts(state) -> dict[str, int]:
    return {
        _hand_token(key): max(0, int(value or 0))
        for key, value in (getattr(state, "hand_play_counts", {}) or {}).items()
    }


def _observed_hand_goals(state) -> set[str]:
    counts = _normalized_play_counts(state)
    total = sum(counts.values())
    if total <= 0:
        return set()
    return {
        hand
        for hand, played in counts.items()
        if played >= 3 and played / total >= 0.30
    }


def _hand_direction(state, hand: str | None = None) -> bool:
    plan_hands = _plan_hand_goals(state)
    observed_hands = _observed_hand_goals(state)
    if hand is None:
        return bool(plan_hands or observed_hands)
    return hand in plan_hands or hand in observed_hands


def _planet_priority(state, planet, original_total: float) -> tuple[float, ...]:
    hand = _hand_token(planet.hand_type)
    plan_owned = 1.0 if hand in _plan_hand_goals(state) else 0.0
    observed_owned = 1.0 if hand in _observed_hand_goals(state) else 0.0
    plays = float(_hand_plays(state, hand))
    sustained_plays = plays if plays >= 3.0 else 0.0
    level = float(_hand_level(state, hand))
    supported_level = level if sustained_plays > 0.0 else 0.0
    practical = float(_PRACTICAL_HAND_PRIORITY.get(hand, 0))
    upgrade = float(getattr(planet, "chips", 0) or 0) + 8.0 * float(
        getattr(planet, "mult", 0) or 0
    )
    return (
        plan_owned,
        observed_owned,
        sustained_plays,
        supported_level,
        practical,
        plays,
        float(original_total),
        upgrade,
    )


def _total_planet_investment(state) -> int:
    return sum(
        max(0, int(level or 1) - 1)
        for level in (getattr(state, "hand_levels", {}) or {}).values()
    )


def _celestial_headroom(state) -> tuple[int, tuple[str, ...]]:
    if has_planet_use_scaler(state):
        return 1, (
            "active Planet-use scaler supplies direct Celestial headroom independent of poker-hand specialization",
        )

    plan_hands = _plan_hand_goals(state)
    observed_hands = _observed_hand_goals(state)
    relevant_hands = plan_hands | observed_hands
    if not relevant_hands:
        return 0, ("no pinned hand goal or strong realized hand specialization",)

    raw_headroom = 0
    relevant_plays = 0
    details: list[str] = []
    for hand in sorted(relevant_hands):
        plays = max(0, _hand_plays(state, hand))
        level = max(1, _hand_level(state, hand))
        relevant_plays += plays
        target_level = 1 + min(3, plays // 4) + (1 if hand in plan_hands else 0)
        target_level = min(5, target_level)
        hand_headroom = max(0, target_level - level)
        raw_headroom += hand_headroom
        details.append(
            f"{hand}:plays={plays},level={level},target={target_level},headroom={hand_headroom}"
        )

    global_budget = max(
        1,
        min(
            5,
            1 + relevant_plays // 6 + (1 if plan_hands else 0),
        ),
    )
    invested = _total_planet_investment(state)
    budget_remaining = max(0, global_budget - invested)
    effective_headroom = min(raw_headroom, budget_remaining)
    return effective_headroom, (
        f"Celestial relevant hands={','.join(sorted(relevant_hands))}",
        *details,
        f"Planet investment={invested}/{global_budget}; remaining={budget_remaining}",
        f"effective Celestial headroom={effective_headroom}",
    )


def _showman_owned(state) -> bool:
    return any(
        _token(
            getattr(joker, "name", None)
            or getattr(joker, "label", None)
            or type(joker).__name__
        )
        in {"SHOWMAN", "SHOWMANJOKER"}
        for joker in tuple(getattr(state, "jokers", ()) or ())
    )


def _held_planet_names(state) -> frozenset[str]:
    return frozenset(
        str(getattr(consumable, "name", "") or "")
        for consumable in tuple(getattr(state, "consumables", ()) or ())
        if str(getattr(consumable, "category", "") or "").upper() == "PLANET"
    )


def _celestial_planet_pool(state) -> tuple[tuple[str, ...], bool, tuple[str, ...]]:
    """Return the current public generatable Planet pool.

    Secret Planets enter only after their public unlock hand has been played. Without
    Showman, held Planet duplicates are excluded and pack offers are drawn without
    replacement. Showman permits duplicate Planet generation.
    """
    showman = _showman_owned(state)
    held = _held_planet_names(state)
    pool: list[str] = []
    excluded: list[str] = []
    for name in eligible_planet_names(state):
        planet = create_planet(name)
        if not showman and planet.name in held:
            excluded.append(planet.name)
            continue
        pool.append(name)
    return tuple(pool), showman, tuple(sorted(excluded))


def _apply_planet_sequence(state, names: tuple[str, ...]):
    projected = deepcopy(state)
    for name in names:
        planet = create_planet(name)
        hand = str(planet.hand_type)
        levels = getattr(projected, "hand_levels", None)
        if not isinstance(levels, dict) or hand not in levels:
            return None
        levels[hand] = int(levels.get(hand, 1) or 1) + 1

        # Constellation is the only current vanilla Planet-use score scaler in the
        # framework. Its public persistent state advances once for each used Planet.
        for joker in tuple(getattr(projected, "jokers", ()) or ()):
            if (
                type(joker).__name__ == "ConstellationJoker"
                and not bool(getattr(joker, "debuffed", False))
            ):
                joker.x_mult = float(getattr(joker, "x_mult", 1.0) or 1.0) + 0.1
    return projected


def _literal_transition_value(state, projected, evaluator: JokerBuildValueEvaluator) -> float | None:
    """Express one permanent Planet transition on D2's literal scoring scale."""
    observed = evaluator._probe_weights(state)
    weighted_gain = 0.0
    total_weight = 0.0

    for hand, template_cards in evaluator._scoring_probes(state):
        cards = deepcopy(list(template_cards))
        before_state = deepcopy(state)
        after_state = deepcopy(projected)
        before_state.hand = deepcopy(cards)
        after_state.hand = deepcopy(cards)
        try:
            before = evaluator.scorer.score(
                hand,
                state=before_state,
                cards=deepcopy(cards),
                resolve_random_effects=False,
            ).total
            after = evaluator.scorer.score(
                hand,
                state=after_state,
                cards=deepcopy(cards),
                resolve_random_effects=False,
            ).total
        except (AttributeError, KeyError, TypeError, ValueError, ZeroDivisionError):
            continue

        gain = (float(after) - float(before)) / max(abs(float(before)), 1.0)
        if observed is None:
            weight = 1.0
        else:
            weight = evaluator._OBSERVED_HAND_PRIOR_WEIGHT + observed.get(
                evaluator._hand_key(hand.value),
                0.0,
            )
        weighted_gain += gain * weight
        total_weight += weight

    if total_weight <= 0.0:
        return None
    normalized_gain = weighted_gain / total_weight
    value = normalized_gain * float(evaluator.weights.direct_scoring_gain)
    value = max(
        -float(evaluator.weights.direct_scoring_cap),
        min(float(evaluator.weights.direct_scoring_cap), value),
    )
    return max(0.0, value)


def _planet_sequence_value(
    state,
    names: tuple[str, ...],
    evaluator: JokerBuildValueEvaluator,
) -> float | None:
    projected = _apply_planet_sequence(state, names)
    if projected is None:
        return None
    return _literal_transition_value(state, projected, evaluator)


def _selection_key(names: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(names))


def _celestial_expected_selection_utility(
    state,
    *,
    offer_count: int,
    selection_count: int,
) -> tuple[float | None, tuple[str, ...]]:
    """Expected best visible Planet selection from the finite public pool.

    Values are literal before/after score transitions on the same direct-scoring
    normalization used by D2. For Mega packs, two selected Planets are simulated as
    one sequential permanent transition so repeated hand levels and Constellation
    growth are not treated as independent bonuses.
    """
    pool, showman, excluded = _celestial_planet_pool(state)
    if not pool or offer_count <= 0 or selection_count <= 0:
        return None, (
            "Celestial public Planet pool unavailable after eligibility/duplicate exclusions",
        )

    draws = max(1, int(offer_count)) if showman else min(len(pool), max(1, int(offer_count)))
    picks = min(max(1, int(selection_count)), draws)
    evaluator = JokerBuildValueEvaluator()

    selection_values: dict[tuple[str, ...], float] = {}
    for size in range(1, picks + 1):
        source = (
            combinations_with_replacement(pool, size)
            if showman
            else combinations(pool, size)
        )
        for names in source:
            key = _selection_key(tuple(names))
            value = _planet_sequence_value(state, key, evaluator)
            if value is None:
                return None, (
                    f"Celestial literal score projection incomplete for selection={key}",
                )
            selection_values[key] = float(value)

    def best_offer_value(offer: tuple[str, ...]) -> float:
        best = 0.0
        for size in range(1, picks + 1):
            for indices in combinations(range(len(offer)), size):
                names = _selection_key(tuple(offer[index] for index in indices))
                best = max(best, selection_values.get(names, 0.0))
        return best

    expected = 0.0
    outcome_count = 0
    if showman:
        denominator = float(len(pool) ** draws)
        for offer in combinations_with_replacement(pool, draws):
            counts = Counter(offer)
            ways = factorial(draws)
            for count in counts.values():
                ways //= factorial(count)
            probability = float(ways) / denominator
            expected += probability * best_offer_value(tuple(offer))
            outcome_count += 1
    else:
        offers = tuple(combinations(pool, draws))
        if not offers:
            return None, ("Celestial offer enumeration produced no outcomes",)
        probability = 1.0 / float(len(offers))
        for offer in offers:
            expected += probability * best_offer_value(tuple(offer))
            outcome_count += 1

    return expected, (
        f"eligible Planet pool={len(pool)}; Showman={'yes' if showman else 'no'}",
        *(
            ("held Planet duplicate exclusions=" + ", ".join(excluded),)
            if excluded
            else ()
        ),
        f"Celestial offers={draws}; selections={picks}; public offer outcomes={outcome_count}",
        f"expected best visible Planet literal value={expected:.3f}",
        "Planet option value uses D2 literal score normalization; no fixed family hit value, RNG seed, or hidden pack identity is used",
    )


def _celestial_visible_hit_probability(
    state,
    offer_count: int,
) -> tuple[float, float, tuple[str, ...]]:
    """Return the public chance of seeing a directionally useful Planet."""
    pool, showman, excluded = _celestial_planet_pool(state)
    pool_size = len(pool)
    if pool_size <= 0 or offer_count <= 0:
        return 0.0, 0.0, ("Celestial Planet pool unavailable; fail closed",)

    if has_planet_use_scaler(state):
        useful_names = set(pool)
        direction = "Planet-use scaler"
    else:
        hands = _plan_hand_goals(state) | _observed_hand_goals(state)
        useful_names = {
            name
            for name in pool
            if _hand_token(create_planet(name).hand_type) in hands
        }
        direction = ",".join(sorted(hands)) or "NONE"

    useful = len(useful_names)
    draws = max(1, int(offer_count)) if showman else min(pool_size, max(0, int(offer_count)))
    per_offer = useful / pool_size
    if useful <= 0:
        at_least_one = 0.0
    elif showman:
        at_least_one = 1.0 - (1.0 - per_offer) ** draws
    elif pool_size - useful < draws:
        at_least_one = 1.0
    else:
        at_least_one = 1.0 - (
            comb(pool_size - useful, draws) / comb(pool_size, draws)
        )
    return per_offer, at_least_one, (
        f"Celestial public pool useful={useful}/{pool_size} direction={direction}",
        f"P(at least one directionally useful Planet in {draws} offers)={at_least_one:.3f}",
        *(
            ("held Planet duplicate exclusions=" + ", ".join(excluded),)
            if excluded
            else ()
        ),
    )


def install_planet_pack_fallback_policy() -> None:
    if getattr(BalatroPackPolicy, "_planet_pack_fallback_installed", False):
        return

    original_rank = BalatroPackPolicy.rank_actions

    def rank_actions(self, state, actions):
        ranked = original_rank(self, state, actions)
        planets: list[tuple[PackActionScore, object]] = []
        for scored in ranked:
            planet = _planet_for_action(scored.action)
            if planet is not None:
                planets.append((scored, planet))
        if not planets:
            return ranked

        best_score, best_planet = max(
            planets,
            key=lambda item: _planet_priority(state, item[1], float(item[0].total)),
        )
        best_hand = _hand_token(best_planet.hand_type)
        mechanically_relevant = (
            has_planet_use_scaler(state)
            or _hand_direction(state, best_hand)
        )
        if not mechanically_relevant or float(best_score.total) <= 0.0:
            return ranked
        current_top = float(ranked[0].total) if ranked else 0.0
        promoted = PackActionScore(
            best_score.action,
            max(float(best_score.total), current_top + 0.001),
            (
                *best_score.notes,
                "Planet pack full-pool selection authority",
                "priority=strategy > observed specialization > sustained plays > supported level > practical fallback > incidental plays",
                f"selected Planet hand={best_hand}",
                "opened Celestial pack cost is sunk and this Planet is mechanically relevant; eligible permanent upgrade beats Skip",
            ),
        )
        return [promoted] + [item for item in ranked if item.action != best_score.action]

    BalatroPackPolicy.rank_actions = rank_actions
    BalatroPackPolicy._planet_pack_fallback_installed = True

    if not getattr(BuildAwareShopBoosterPolicy, "_planet_spend_guard_installed", False):
        original_booster_recommend = BuildAwareShopBoosterPolicy.recommend

        def booster_recommend(self, state, action):
            result = original_booster_recommend(self, state, action)
            if result.family != "CELESTIAL" or int(result.offer_count) <= 0:
                return result

            per_offer, at_least_one, probability_notes = _celestial_visible_hit_probability(
                state,
                result.offer_count,
            )
            option_utility, expectation_notes = _celestial_expected_selection_utility(
                state,
                offer_count=int(result.offer_count),
                selection_count=int(result.selection_count),
            )
            if option_utility is None:
                return replace(
                    result,
                    decision=HOLD,
                    rationale=(
                        *result.rationale,
                        *probability_notes,
                        *expectation_notes,
                        "Celestial literal expectation incomplete; HOLD fails closed",
                    ),
                )

            price = self._price(action.target)
            resource_cost = self.resource_valuator.money_spend_cost(
                money=int(state.money),
                spend=price,
                price_weight=self.thresholds.price_weight,
                interest_weight=self.thresholds.interest_weight,
                reserve_target=self.thresholds.reserve_target,
                reserve_weight=self.thresholds.reserve_weight,
                vouchers=getattr(state, "vouchers", ()),
                jokers=getattr(state, "jokers", ()),
            )
            advantage = float(option_utility) - float(resource_cost.total)
            decision = (
                "BUY"
                if float(option_utility) > 0.0
                and advantage > float(self.thresholds.minimum_buy_advantage)
                else HOLD
            )
            superseded_prefixes = (
                "per-offer useful-choice prior=",
                "P(at least one useful visible offer)=",
                "option EV=",
                "D8 advantage over SAVE=0 is ",
                "price penalty=",
                "interest penalty=",
                "reserve penalty=",
                "hit-probability threshold=",
            )
            rationale = tuple(
                note
                for note in result.rationale
                if not str(note).startswith(superseded_prefixes)
            )
            result = replace(
                result,
                decision=decision,
                total=float(self.parent_hold_baseline) + advantage,
                advantage_over_save=advantage,
                option_utility=float(option_utility),
                per_offer_hit_probability=per_offer,
                at_least_one_hit_probability=at_least_one,
                price_penalty=float(resource_cost.direct),
                interest_penalty=float(resource_cost.interest),
                reserve_penalty=float(resource_cost.reserve),
                rationale=(
                    *rationale,
                    *probability_notes,
                    *expectation_notes,
                    f"Celestial shared resource cost={resource_cost.total:.3f}",
                    *resource_cost.notes,
                    f"Celestial literal advantage over SAVE=0 is {advantage:.3f}; required>{self.thresholds.minimum_buy_advantage:.3f}",
                    "finite public Planet expectation supersedes the generic family hit-value and hit-probability admission heuristic",
                ),
            )

            headroom, headroom_notes = _celestial_headroom(state)
            hold_reason = None
            if headroom <= 0:
                hold_reason = "Celestial purchase held: no marginal hand-development headroom"
            else:
                reserve_target = int(self.thresholds.reserve_target)
                money_after = int(state.money) - int(price)
                if money_after < reserve_target:
                    hold_reason = (
                        "Celestial purchase held: purchase would "
                        f"leave ${money_after} below ${reserve_target} reserve"
                    )

            if hold_reason is None:
                return replace(result, rationale=(*result.rationale, *headroom_notes))

            return replace(
                result,
                decision=HOLD,
                rationale=(*result.rationale, *headroom_notes, hold_reason),
            )

        BuildAwareShopBoosterPolicy.recommend = booster_recommend
        BuildAwareShopBoosterPolicy._planet_spend_guard_installed = True

    if not getattr(ConsumableAcquisitionPolicy, "_loose_consumable_spend_guard_installed", False):
        original_consumable_decide = ConsumableAcquisitionPolicy.decide

        def consumable_decide(self, state, candidate):
            result = original_consumable_decide(self, state, candidate)
            selected = result.selected
            if selected is None or result.action not in {BUY, BUY_AND_USE}:
                return result

            category = str(getattr(candidate, "category", "") or "").upper()
            if category == "TAROT" and result.action == BUY:
                if float(selected.total_advantage) >= 1.00:
                    return result
                return ConsumableAcquisitionDecision(
                    action=HOLD,
                    candidate=result.candidate,
                    selected=None,
                    options=result.options,
                    thresholds=result.thresholds,
                    rationale=(
                        *result.rationale,
                        "loose Tarot held: non-immediate purchase requires >=1.00 transaction advantage",
                    ),
                )

            return result

        ConsumableAcquisitionPolicy.decide = consumable_decide
        ConsumableAcquisitionPolicy._loose_consumable_spend_guard_installed = True
