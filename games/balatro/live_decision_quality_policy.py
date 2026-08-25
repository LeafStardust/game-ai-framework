from __future__ import annotations

"""Stable live decision-quality guards derived from production validation.

These are authority corrections, not tuning knobs:
- zero-cost autonomous-safe boosters are opened when ordinary/default D8 semantics
  would otherwise reject them only for value/probability reasons;
- off-build exotic Planets cannot bootstrap relevance from a stray level increase;
- weak Joker replacement churn is suppressed unless it materially improves the build;
- pack Planet relevance uses the same applied-strategy-aware exotic-hand rule.
"""

from dataclasses import replace

from games.balatro.actions import BUY_BOOSTER
from games.balatro.bonds.evaluation import evaluate_bond_composition
from games.balatro.build_health_runtime import projected_state_with_jokers
from games.balatro.joker_policy import HOLD, REPLACE
from games.balatro.pack_policy import BalatroPackPolicy, PackActionScore
from games.balatro.planets import PLANET_CARDS
from games.balatro.playbook.red_white.joker_policy import PlaybookJokerAcquisitionPolicy
from games.balatro.shop_booster_policy import (
    BUY,
    BoosterAcquisitionThresholds,
    BuildAwareShopBoosterPolicy,
)
import games.balatro.planet_relevance_policy as planet_relevance


_MIN_UNPINNED_REPLACEMENT_ADVANTAGE = 1.50
_MIN_SAME_PLAN_STRENGTH_GAIN = 1.00
_MIN_SAME_PLAN_COMPLETION_GAIN = 0.03
_STRONG_LOCAL_REPLACEMENT_ADVANTAGE = 2.50

# These hands are rare enough that a Planet level by itself must not create its own
# justification. This is the Neptune failure observed live: Straight Flush reached
# level 2/3 while its play count remained exactly zero.
_EXOTIC_HANDS = frozenset(
    {
        "STRAIGHT_FLUSH",
        "FIVE_OF_A_KIND",
        "FLUSH_HOUSE",
        "FLUSH_FIVE",
    }
)


def _token(value: object) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def _hand_key(value: object) -> str:
    return "_".join(str(value or "").strip().upper().replace("-", " ").replace("_", " ").split())


def _plan_hand_bond(hand_type: str) -> str:
    return {
        "HIGH_CARD": "high_card",
        "PAIR": "pair",
        "TWO_PAIR": "two_pair",
        "THREE_OF_A_KIND": "three_kind",
        "FOUR_OF_A_KIND": "four_kind",
        "STRAIGHT": "straight",
        "FLUSH": "flush",
        "FULL_HOUSE": "full_house",
        "STRAIGHT_FLUSH": "straight_flush",
        "FIVE_OF_A_KIND": "five_kind",
        "FLUSH_HOUSE": "flush_house",
        "FLUSH_FIVE": "flush_five",
    }.get(_hand_key(hand_type), "")


def _strategy_plan(state):
    try:
        _, composition = evaluate_bond_composition(state)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        return None, None
    return composition, getattr(composition, "strategy_plan", None)


def _strict_planet_hand_relevant(state, candidate):
    hand_type = _hand_key(getattr(candidate, "hand_type", ""))
    if not hand_type:
        return False, ("Planet target hand is unavailable",)

    bond_id = _plan_hand_bond(hand_type)
    composition, plan = _strategy_plan(state)
    if plan is not None and bond_id:
        planned = {goal.bond_id for goal in tuple(getattr(plan, "bond_goals", ()) or ())}
        if bond_id in planned:
            return True, (f"Planet target {hand_type} is an applied Strategy Plan Bond goal",)

    if composition is not None and bond_id:
        pinned_id = getattr(composition, "pinned_strategy_id", None)
        for strategy in tuple(getattr(composition, "strategy_candidates", ()) or ()):
            if strategy.strategy_id == pinned_id and bond_id in tuple(strategy.bond_ids or ()):
                return True, (f"Planet target {hand_type} belongs to pinned strategy {pinned_id}",)

    plays = getattr(state, "hand_play_counts", {}) or {}
    played = int(plays.get(hand_type, 0) or 0)
    total = sum(max(0, int(value or 0)) for value in plays.values())
    concentration = played / total if total > 0 else 0.0
    level = int((getattr(state, "hand_levels", {}) or {}).get(hand_type, 1) or 1)

    # Preserve canonical B4/D9 behavior for ordinary developed hands. A levelled Pair,
    # Straight, Flush, etc. is legitimate build-path evidence even when the synthetic
    # test state has no play-count telemetry.
    if hand_type not in _EXOTIC_HANDS and level > 1:
        return True, (f"Planet target {hand_type} is already developed to level {level}",)

    if played >= 3 and concentration >= 0.20:
        return True, (
            f"Planet target {hand_type} has sustained use: plays={played}, concentration={concentration:.3f}",
        )
    if level >= 3 and played >= 2 and concentration >= 0.15:
        return True, (
            f"Planet target {hand_type} has sustained developed use: level={level}, plays={played}, concentration={concentration:.3f}",
        )

    if played == 0:
        return False, (
            f"Planet target {hand_type} has zero play history; level={level} is insufficient off-plan evidence",
            f"Planet target {hand_type} is off-plan/weak-history: level={level}, plays=0, concentration=0.000",
        )
    return False, (
        f"Planet target {hand_type} is off-plan/weak-history: level={level}, plays={played}, concentration={concentration:.3f}",
    )


def _planet_candidate_from_label(label: str):
    target = _token(label)
    for planet in PLANET_CARDS.values():
        if _token(planet.name) == target:
            return planet
    return None


def _default_d8_thresholds(policy: BuildAwareShopBoosterPolicy) -> bool:
    """Return whether D8 is using the canonical default admission thresholds."""
    return policy.thresholds == BoosterAcquisitionThresholds()


def _free_booster_safe_to_open(state, result) -> bool:
    """Open only families whose post-open path is already autonomous-safe.

    Arcana/Spectral remain HOLD because their follow-up safety is intentionally
    deferred to D9/D10. Buffoon still requires capacity because PACK_SELECT cannot
    autonomously sell an incumbent first.
    """
    family = str(getattr(result, "family", "") or "").upper()
    if family in {"STANDARD", "CELESTIAL"}:
        return True
    if family == "BUFFOON":
        jokers = tuple(getattr(state, "jokers", ()) or ())
        slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
        return len(jokers) < slots
    return False


def install_live_decision_quality_policy() -> None:
    # Zero-cost autonomous-safe packs have no resource downside, but this authority
    # must not bypass custom playbook D8 thresholds or families whose post-open
    # transaction contract is intentionally deferred.
    if not getattr(BuildAwareShopBoosterPolicy, "_free_booster_authority_installed", False):
        original_booster_recommend = BuildAwareShopBoosterPolicy.recommend

        def recommend(self, state, action):
            result = original_booster_recommend(self, state, action)
            if action.name != BUY_BOOSTER:
                return result
            try:
                price = int(self._price(action.target))
            except (AttributeError, TypeError, ValueError):
                return result
            if (
                price != 0
                or result.family is None
                or not _default_d8_thresholds(self)
                or not _free_booster_safe_to_open(state, result)
            ):
                return result
            return replace(
                result,
                decision=BUY,
                total=max(float(result.total), float(self.parent_hold_baseline) + max(0.50, float(result.option_utility))),
                advantage_over_save=max(float(result.advantage_over_save), 0.50, float(result.option_utility)),
                price_penalty=0.0,
                interest_penalty=0.0,
                reserve_penalty=0.0,
                rationale=(
                    *result.rationale,
                    "FREE BOOSTER AUTHORITY: $0 autonomous-safe pack is opened; post-open Skip remains available",
                ),
            )

        BuildAwareShopBoosterPolicy.recommend = recommend
        BuildAwareShopBoosterPolicy._free_booster_authority_installed = True

    # Replace the permissive exotic-hand rule with applied-plan-aware sustained
    # relevance. Ordinary developed hand paths retain canonical B4 semantics.
    planet_relevance._planet_hand_relevant = _strict_planet_hand_relevant

    if not getattr(BalatroPackPolicy, "_strict_planet_relevance_installed", False):
        original_pack_score = BalatroPackPolicy.score_action

        def score_action(self, state, action):
            scored = original_pack_score(self, state, action)
            choice = getattr(scored.action, "target", None)
            if str(getattr(choice, "kind", "") or "").upper() != "PLANET":
                return scored
            candidate = _planet_candidate_from_label(str(getattr(choice, "label", "") or ""))
            if candidate is None:
                return scored
            relevant, notes = _strict_planet_hand_relevant(state, candidate)
            if relevant:
                return PackActionScore(scored.action, scored.total, (*scored.notes, *notes))
            return PackActionScore(
                scored.action,
                min(-1.0, float(getattr(self, "skip_bias", 0.35)) - 1.0),
                (*scored.notes, *notes, "off-build exotic Planet veto applies inside booster packs too"),
            )

        BalatroPackPolicy.score_action = score_action
        BalatroPackPolicy._strict_planet_relevance_installed = True

    if not getattr(PlaybookJokerAcquisitionPolicy, "_replacement_stability_installed", False):
        original_joker_decide = PlaybookJokerAcquisitionPolicy.decide

        def decide(self, state, candidate):
            decision = original_joker_decide(self, state, candidate)
            if decision.action != REPLACE or decision.selected is None:
                return decision
            selected = decision.selected
            advantage = float(getattr(selected, "total_advantage", 0.0) or 0.0)
            try:
                index = int(selected.replace_index)
            except (TypeError, ValueError):
                return decision

            current_comp, current_plan = _strategy_plan(state)
            if current_plan is None:
                if advantage >= _MIN_UNPINNED_REPLACEMENT_ADVANTAGE:
                    return decision
                return replace(
                    decision,
                    action=HOLD,
                    selected=None,
                    rationale=(
                        *decision.rationale,
                        f"replacement stability veto: advantage={advantage:.3f} < {_MIN_UNPINNED_REPLACEMENT_ADVANTAGE:.3f}",
                        "avoid low-confidence Joker churn before an applied strategy exists",
                    ),
                )

            jokers = list(getattr(state, "jokers", ()) or ())
            if index < 0 or index >= len(jokers):
                return decision
            jokers[index] = candidate
            projected_state = projected_state_with_jokers(state, tuple(jokers))
            projected_comp, projected_plan = _strategy_plan(projected_state)
            if projected_plan is None:
                return decision
            if projected_plan.strategy_id != current_plan.strategy_id:
                return decision

            current_completion = float(getattr(current_plan, "completion", 0.0) or 0.0)
            projected_completion = float(getattr(projected_plan, "completion", 0.0) or 0.0)
            completion_gain = projected_completion - current_completion

            def pinned_strength(comp, strategy_id):
                if comp is None:
                    return 0.0
                for item in tuple(getattr(comp, "strategy_candidates", ()) or ()):
                    if item.strategy_id == strategy_id:
                        return float(getattr(item, "strength", 0.0) or 0.0)
                return 0.0

            strength_gain = pinned_strength(projected_comp, current_plan.strategy_id) - pinned_strength(current_comp, current_plan.strategy_id)
            if (
                completion_gain >= _MIN_SAME_PLAN_COMPLETION_GAIN
                or strength_gain >= _MIN_SAME_PLAN_STRENGTH_GAIN
                or advantage >= _STRONG_LOCAL_REPLACEMENT_ADVANTAGE
            ):
                return decision

            return replace(
                decision,
                action=HOLD,
                selected=None,
                rationale=(
                    *decision.rationale,
                    f"same-plan replacement stability veto: completion delta={completion_gain:.3f}, strength delta={strength_gain:.3f}, advantage={advantage:.3f}",
                    "replacement must materially advance the applied Strategy Plan or be a strong local upgrade",
                ),
            )

        PlaybookJokerAcquisitionPolicy.decide = decide
        PlaybookJokerAcquisitionPolicy._replacement_stability_installed = True
