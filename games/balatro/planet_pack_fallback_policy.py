from __future__ import annotations

"""Final Planet selection and acquisition discipline.

Opened Celestial packs should almost always yield a Planet: once the pack cost is
sunk, every offered Planet is a permanent scoring upgrade. Rank the complete Planet
pool by canonical strategy direction, realized hand development, practical hand
realisability, and only then generic card value.

Acquisition remains a separate resource decision. Celestial packs require actual
hand-development headroom and obey a diminishing global Planet-investment budget;
loose Planets require hand relevance; loose Tarots require stronger transaction
value unless immediately usable. Arcana pack acquisition is not changed here.

An active Planet-use scaler is a stronger mechanical authority than ordinary hand-
development headroom: every Planet is direct permanent engine progress. Reserve
protection remains authoritative.
"""

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.planet_scaler_authority import has_planet_use_scaler
from games.balatro.planets import PLANET_CARDS
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
        current_top = float(ranked[0].total) if ranked else 0.0
        promoted = PackActionScore(
            best_score.action,
            max(float(best_score.total), current_top + 0.001),
            (
                *best_score.notes,
                "Planet pack full-pool selection authority",
                "priority=strategy > observed specialization > sustained plays > supported level > practical fallback > incidental plays",
                f"selected Planet hand={best_hand}",
                "opened Celestial pack cost is sunk; offered permanent upgrade beats Skip",
            ),
        )
        return [promoted] + [item for item in ranked if item.action != best_score.action]

    BalatroPackPolicy.rank_actions = rank_actions
    BalatroPackPolicy._planet_pack_fallback_installed = True

    if not getattr(BuildAwareShopBoosterPolicy, "_planet_spend_guard_installed", False):
        original_booster_recommend = BuildAwareShopBoosterPolicy.recommend

        def booster_recommend(self, state, action):
            result = original_booster_recommend(self, state, action)
            if result.family != "CELESTIAL" or not result.should_buy:
                return result

            headroom, headroom_notes = _celestial_headroom(state)
            hold_reason = None
            if headroom <= 0:
                hold_reason = "Celestial purchase held: no marginal hand-development headroom"
            else:
                price = self._price(action.target)
                reserve_target = int(self.thresholds.reserve_target)
                money_after = int(state.money) - int(price)
                if money_after < reserve_target:
                    hold_reason = (
                        "Celestial purchase held: purchase would "
                        f"leave ${money_after} below ${reserve_target} reserve"
                    )

            if hold_reason is None:
                return type(result)(
                    decision=result.decision,
                    action=result.action,
                    family=result.family,
                    variant=result.variant,
                    total=result.total,
                    advantage_over_save=result.advantage_over_save,
                    option_utility=result.option_utility,
                    build_need_score=result.build_need_score,
                    per_offer_hit_probability=result.per_offer_hit_probability,
                    at_least_one_hit_probability=result.at_least_one_hit_probability,
                    offer_count=result.offer_count,
                    selection_count=result.selection_count,
                    runway_factor=result.runway_factor,
                    price_penalty=result.price_penalty,
                    interest_penalty=result.interest_penalty,
                    reserve_penalty=result.reserve_penalty,
                    rationale=(*result.rationale, *headroom_notes),
                )

            return type(result)(
                decision=HOLD,
                action=result.action,
                family=result.family,
                variant=result.variant,
                total=result.total,
                advantage_over_save=result.advantage_over_save,
                option_utility=result.option_utility,
                build_need_score=result.build_need_score,
                per_offer_hit_probability=result.per_offer_hit_probability,
                at_least_one_hit_probability=result.at_least_one_hit_probability,
                offer_count=result.offer_count,
                selection_count=result.selection_count,
                runway_factor=result.runway_factor,
                price_penalty=result.price_penalty,
                interest_penalty=result.interest_penalty,
                reserve_penalty=result.reserve_penalty,
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
            if category == "PLANET":
                # D4 already made the reserve-safe mechanical decision. A Planet-use
                # scaler turns every usable Planet into immediate permanent engine
                # progress, so generic loose-Planet relevance must not undo it.
                if has_planet_use_scaler(state) and result.action == BUY_AND_USE:
                    return result
                hand = _hand_token(getattr(candidate, "hand_type", ""))
                if _hand_direction(state, hand) and float(selected.total_advantage) >= 0.75:
                    return result
                return ConsumableAcquisitionDecision(
                    action=HOLD,
                    candidate=result.candidate,
                    selected=None,
                    options=result.options,
                    thresholds=result.thresholds,
                    rationale=(
                        *result.rationale,
                        "loose Planet held: requires hand-development relevance and >=0.75 transaction advantage",
                    ),
                )

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
