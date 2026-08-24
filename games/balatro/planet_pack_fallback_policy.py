from __future__ import annotations

"""Final Planet selection and acquisition discipline.

Opened Celestial packs should almost always yield a Planet: once the pack cost is
sunk, every valid Planet is a permanent scoring upgrade.  Rank the complete Planet
pool by canonical strategy direction, realized hand development, and generic upgrade
value instead of limiting fallback authority to a small hand subset.

Acquisition remains a separate resource decision.  Celestial packs and loose
Planets require actual hand-development evidence; loose Tarots require stronger
transaction value unless they are immediately usable.  Arcana pack acquisition is
not changed here.
"""

from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.bonds.strategy_semantics import StrategyCommitment
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.planets import PLANET_CARDS
from games.balatro.shop_booster_policy import HOLD, BuildAwareShopBoosterPolicy
from games.balatro.shop_consumable_policy import (
    BUY,
    BUY_AND_USE,
    ConsumableAcquisitionDecision,
    ConsumableAcquisitionPolicy,
)


def _token(value: object) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


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


def _hand_direction(state, hand: str | None = None) -> bool:
    plan_hands = _plan_hand_goals(state)
    if hand is not None and hand in plan_hands:
        return True
    if hand is None and plan_hands:
        return True

    counts = {
        str(key).upper().replace(" ", "_"): max(0, int(value or 0))
        for key, value in (getattr(state, "hand_play_counts", {}) or {}).items()
    }
    total = sum(counts.values())
    if hand is not None:
        played = counts.get(hand, _hand_plays(state, hand))
        concentration = played / total if total > 0 else 0.0
        return played >= 3 and concentration >= 0.30

    top = max(counts.values(), default=0)
    concentration = top / total if total > 0 else 0.0
    return top >= 4 and concentration >= 0.40


def _planet_priority(state, planet, original_total: float) -> tuple[float, ...]:
    hand = str(planet.hand_type).upper().replace(" ", "_")
    plan_owned = 1.0 if hand in _plan_hand_goals(state) else 0.0
    plays = float(_hand_plays(state, hand))
    level = float(_hand_level(state, hand))
    # All Planet upgrades are permanent.  Chips/mult are only a final generic
    # tie-breaker after strategy and realized play evidence.
    upgrade = float(getattr(planet, "chips", 0) or 0) + 8.0 * float(
        getattr(planet, "mult", 0) or 0
    )
    return (plan_owned, plays, level, upgrade, float(original_total))


def install_planet_pack_fallback_policy() -> None:
    if getattr(BalatroPackPolicy, "_planet_pack_fallback_installed", False):
        return

    original_rank = BalatroPackPolicy.rank_actions

    def rank_actions(self, state, actions):
        ranked = original_rank(self, state, actions)
        planets: list[tuple[PackActionScore, object]] = []
        for scored in ranked:
            planet = _planet_for_action(scored.action)
            if planet is not None and planet.hand_type in (getattr(state, "hand_levels", {}) or {}):
                planets.append((scored, planet))
        if not planets:
            return ranked

        best_score, best_planet = max(
            planets,
            key=lambda item: _planet_priority(state, item[1], float(item[0].total)),
        )
        best_hand = str(best_planet.hand_type).upper().replace(" ", "_")
        current_top = float(ranked[0].total) if ranked else 0.0
        promoted = PackActionScore(
            best_score.action,
            max(float(best_score.total), current_top + 0.001),
            (
                *best_score.notes,
                "Planet pack full-pool selection authority",
                "priority=strategy hand > realized plays > developed level > generic upgrade",
                f"selected Planet hand={best_hand}",
                "opened Celestial pack cost is sunk; valid permanent upgrade beats Skip",
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
            if _hand_direction(state):
                return result
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
                rationale=(
                    *result.rationale,
                    "Celestial purchase held: no pinned hand goal or strong realized hand specialization",
                ),
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
                hand = str(getattr(candidate, "hand_type", "") or "").upper().replace(" ", "_")
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
