from __future__ import annotations

"""Build-quality calibration from the latest Red/White five-run batch.

This policy addresses two public-state failure modes without predicting hidden shop
contents:

* weak full Joker boards could retain low-impact slots because a genuinely positive
  replacement failed the ordinary replacement-margin threshold;
* repeated poker-hand specialization could remain unable to buy its matching Planet
  because formal strategy status had not yet reached HIGHLIGHTED.

The replacement relaxation is deliberately narrow: the current build must be weak,
the roster must be full, the original planner must already consider the replacement
eligible, whole-build delta must be positive, and the hypothetical replacement must
improve immediate/scaling Build Health (or replace a non-scoring slot with a real
scorer). Existing committed-build protections therefore remain authoritative.
"""

from copy import deepcopy
from dataclasses import replace

from games.balatro.build_health_runtime import RuntimeBuildHealthEvaluator
from games.balatro.strategy import BRONZE, GOLD, SILVER
from games.balatro.strategy_value import (
    StrategyAdjustedConsumableEvaluation,
    StrategyAwareConsumableSynergyEvaluator,
    StrategyAwareJokerBuildTransitionPlanner,
)


_HEALTH = RuntimeBuildHealthEvaluator()
_POSITIVE_TIERS = {GOLD, SILVER, BRONZE}


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def _ante(state) -> int:
    return max(1, int(getattr(state, "ante", 1) or 1))


def _full_joker_roster(state) -> bool:
    slots = max(0, int(getattr(state, "joker_slots", 0) or 0))
    return slots > 0 and len(getattr(state, "jokers", ()) or ()) >= slots


def _direct_scoring_gain(value: object) -> float:
    try:
        return float(getattr(value, "direct_scoring_gain", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _weak_health(health) -> bool:
    return bool(
        getattr(health, "critical", False)
        or getattr(health, "scaling_deficit", False)
        or float(getattr(health, "survival", 100.0)) < 75.0
        or float(getattr(health, "immediate", 100.0)) < 70.0
    )


def _hypothetical_replacement_state(state, index: int, candidate: object):
    simulated = deepcopy(state)
    jokers = list(getattr(simulated, "jokers", ()) or ())
    if not 0 <= int(index) < len(jokers):
        return None
    jokers[int(index)] = deepcopy(candidate)
    simulated.jokers = jokers
    return simulated


def _health_improvement(before, after) -> tuple[float, float, float]:
    immediate = float(getattr(after, "immediate", 0.0)) - float(
        getattr(before, "immediate", 0.0)
    )
    scaling = float(getattr(after, "scaling", 0.0)) - float(
        getattr(before, "scaling", 0.0)
    )
    total = float(getattr(after, "total", 0.0)) - float(
        getattr(before, "total", 0.0)
    )
    return immediate, scaling, total


def _replacement_qualifies(state, candidate: object, option, before_health):
    if not bool(getattr(option, "eligible", False)):
        return None
    try:
        build_delta = float(getattr(option, "build_delta", 0.0) or 0.0)
    except (TypeError, ValueError):
        return None
    if build_delta <= 0.0:
        return None

    index = int(getattr(option, "replace_index", -1))
    simulated = _hypothetical_replacement_state(state, index, candidate)
    if simulated is None:
        return None
    after_health = _HEALTH.evaluate(simulated)
    immediate_gain, scaling_gain, total_gain = _health_improvement(
        before_health,
        after_health,
    )

    incumbent_value = getattr(option, "incumbent_value", None)
    candidate_value = getattr(option, "candidate_value", None)
    incumbent_direct = _direct_scoring_gain(incumbent_value)
    candidate_direct = _direct_scoring_gain(candidate_value)
    replaces_non_scoring_slot = (
        incumbent_direct <= 1e-9
        and candidate_direct > incumbent_direct + 1e-9
    )
    material_health_gain = (
        scaling_gain >= 5.0
        or immediate_gain >= 7.5
        or (
            total_gain >= 4.0
            and immediate_gain > 0.0
            and scaling_gain > 0.0
        )
    )
    if not (replaces_non_scoring_slot or material_health_gain):
        return None

    return (
        option,
        immediate_gain,
        scaling_gain,
        total_gain,
        incumbent_direct,
        candidate_direct,
    )


def _hand_play_counts(state) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key, value in (getattr(state, "hand_play_counts", {}) or {}).items():
        token = _normalize(getattr(key, "value", key))
        if not token:
            continue
        try:
            amount = max(0, int(value or 0))
        except (TypeError, ValueError):
            amount = 0
        counts[token] = counts.get(token, 0) + amount
    return counts


def observed_hand_specialization(state, hand_type: object) -> tuple[bool, int, int]:
    """Return whether public hand history strongly specializes in ``hand_type``.

    Eight observed plays and a 3:2 lead over the runner-up are intentionally
    conservative: this fallback should represent empirical commitment, not ordinary
    early exploration.
    """

    target = _normalize(getattr(hand_type, "value", hand_type))
    counts = _hand_play_counts(state)
    target_count = counts.get(target, 0)
    runner_up = max(
        (count for hand, count in counts.items() if hand != target),
        default=0,
    )
    specialized = (
        target_count >= 8
        and target_count * 2 >= max(1, runner_up) * 3
    )
    return specialized, target_count, runner_up


def install_latest_batch_build_quality_policy() -> None:
    if getattr(
        StrategyAwareJokerBuildTransitionPlanner,
        "_latest_batch_build_quality_installed",
        False,
    ):
        return

    original_plan = StrategyAwareJokerBuildTransitionPlanner.plan

    def plan(self, state, candidate):
        transition = original_plan(self, state, candidate)
        if (
            getattr(transition, "action", "") == "REPLACE"
            or _ante(state) < 3
            or not _full_joker_roster(state)
            or not getattr(transition, "alternatives", ())
        ):
            return transition

        before_health = _HEALTH.evaluate(state)
        if not _weak_health(before_health):
            return transition

        qualified = []
        for option in transition.alternatives:
            result = _replacement_qualifies(
                state,
                candidate,
                option,
                before_health,
            )
            if result is not None:
                qualified.append(result)
        if not qualified:
            return transition

        selected = max(
            qualified,
            key=lambda item: (
                item[2],  # scaling gain
                item[1],  # immediate gain
                item[3],  # total Build Health gain
                float(getattr(item[0], "build_delta", 0.0) or 0.0),
                -int(getattr(item[0], "replace_index", 0)),
            ),
        )
        option, immediate_gain, scaling_gain, total_gain, incumbent_direct, candidate_direct = selected
        return replace(
            transition,
            action="REPLACE",
            replacement=option,
            rationale=(
                *tuple(getattr(transition, "rationale", ()) or ()),
                "latest-batch build-quality pressure: weak full roster may accept a positive whole-build replacement below the ordinary margin",
                f"Build Health immediate gain={immediate_gain:+.3f}; scaling gain={scaling_gain:+.3f}; total gain={total_gain:+.3f}",
                f"direct scoring gain incumbent={incumbent_direct:.3f}; candidate={candidate_direct:.3f}",
                "original eligibility remains authoritative, so committed/Negative/safety protections are not bypassed",
            ),
        )

    StrategyAwareJokerBuildTransitionPlanner.plan = plan
    StrategyAwareJokerBuildTransitionPlanner._latest_batch_build_quality_installed = True

    original_consumable_evaluate = StrategyAwareConsumableSynergyEvaluator.evaluate

    def evaluate(self, candidate, state, *, profile=None):
        result = original_consumable_evaluate(
            self,
            candidate,
            state,
            profile=profile,
        )
        if str(getattr(candidate, "category", "")).upper() != "PLANET":
            return result

        specialized, observed, runner_up = observed_hand_specialization(
            state,
            getattr(candidate, "hand_type", ""),
        )
        if not specialized:
            return result

        strategic = self.strategy_tracker.evaluate_item(state, candidate, kind="PLANET")
        if strategic.tier not in _POSITIVE_TIERS:
            return result

        base = getattr(result, "base_evaluation", None)
        if base is None:
            return result
        base_gain = float(getattr(base, "total_gain", 0.0) or 0.0)
        restored_adjustment = max(0.0, float(getattr(strategic, "value", 0.0) or 0.0))
        restored_total = base_gain + restored_adjustment
        if restored_total <= float(getattr(result, "total_gain", 0.0) or 0.0):
            return result

        return replace(
            result,
            total_gain=restored_total,
            strategic_adjustment=restored_adjustment,
            rationale=(
                *tuple(getattr(base, "rationale", ()) or ()),
                *tuple(getattr(strategic, "rationale", ()) or ()),
                "latest-batch Planet alignment fallback: strong public hand history establishes empirical commitment even before formal HIGHLIGHTED status",
                f"matching hand observed plays={observed}; runner-up={runner_up}",
                f"restored existing Planet relationship value={restored_adjustment:+.3f}",
                f"empirically aligned Planet whole-build gain={restored_total:.3f}",
            ),
        )

    StrategyAwareConsumableSynergyEvaluator.evaluate = evaluate
    StrategyAwareConsumableSynergyEvaluator._latest_batch_build_quality_installed = True
