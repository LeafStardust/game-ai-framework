from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Mapping

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner, LiveBlindPlan


@dataclass(frozen=True)
class HandActionThresholds:
    """Thresholds owned only by D1: play-vs-discard and hand subset choice."""

    play_clear_probability_floor: float = 0.75
    discard_clear_probability_advantage: float = 0.05
    discard_progress_advantage: float = 0.08
    low_discard_reserve: int = 1
    low_discard_extra_clear_advantage: float = 0.05
    low_discard_extra_progress_advantage: float = 0.04
    low_hand_reserve: int = 1
    low_hand_clear_advantage_discount: float = 0.03
    low_hand_progress_advantage_discount: float = 0.03

    def __post_init__(self) -> None:
        probability_fields = (
            "play_clear_probability_floor",
            "discard_clear_probability_advantage",
            "discard_progress_advantage",
            "low_discard_extra_clear_advantage",
            "low_discard_extra_progress_advantage",
            "low_hand_clear_advantage_discount",
            "low_hand_progress_advantage_discount",
        )
        for name in probability_fields:
            value = float(getattr(self, name))
            if value < 0.0 or value > 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.low_discard_reserve < 0:
            raise ValueError("low_discard_reserve cannot be negative")
        if self.low_hand_reserve < 0:
            raise ValueError("low_hand_reserve cannot be negative")

    @classmethod
    def from_mapping(cls, value: Mapping[str, object] | None) -> "HandActionThresholds":
        if not value:
            return cls()
        allowed = {field.name for field in fields(cls)}
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError(
                "unknown D1 hand-action threshold(s): " + ", ".join(unknown)
            )
        return cls(**{name: value[name] for name in allowed if name in value})

    def as_dict(self) -> dict[str, float | int]:
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class HandActionDecision:
    action: BalatroAction
    selected_plan: LiveBlindPlan
    best_play: LiveBlindPlan
    best_discard: LiveBlindPlan | None
    thresholds: HandActionThresholds
    required_discard_clear_advantage: float
    required_discard_progress_advantage: float
    clear_probability_delta: float | None
    progress_delta: float | None
    confidence: float
    rationale: tuple[str, ...]
    candidate_count: int


class LiveHandActionThresholdPolicy:
    """D1 policy: choose the exact Play/Discard action from planner estimates.

    The expectimax planner supplies public-state outcomes. This policy owns the
    strategic boundary between spending a hand and spending a discard. It does not
    reuse shop, consumable, pack, voucher or economy thresholds.
    """

    EPSILON = 1e-12

    def __init__(self, thresholds: HandActionThresholds | None = None) -> None:
        self.thresholds = thresholds or HandActionThresholds()

    def decide(self, state, plans: list[LiveBlindPlan]) -> HandActionDecision:
        plays = [plan for plan in plans if plan.action.name == PLAY_CARDS]
        discards = [plan for plan in plans if plan.action.name == DISCARD_CARDS]
        if not plays:
            raise ValueError("D1 requires at least one PLAY_CARDS candidate")

        best_play = max(plays, key=self._within_type_key)
        best_discard = max(discards, key=self._within_type_key) if discards else None
        clear_requirement, progress_requirement = self._discard_requirements(state)

        if best_discard is None or int(getattr(state, "discards_remaining", 0)) <= 0:
            return self._decision(
                best_play,
                best_play,
                None,
                clear_requirement,
                progress_requirement,
                None,
                None,
                1.0,
                ("no legal discard candidate; play the best subset",),
                len(plans),
            )

        play_value = best_play.value
        discard_value = best_discard.value
        clear_delta = (
            discard_value.clear_probability - play_value.clear_probability
        )
        progress_delta = discard_value.expected_progress - play_value.expected_progress

        if play_value.clear_probability >= 1.0 - self.EPSILON:
            return self._decision(
                best_play,
                best_play,
                best_discard,
                clear_requirement,
                progress_requirement,
                clear_delta,
                progress_delta,
                1.0,
                ("best play is a certain blind clear",),
                len(plans),
            )

        if clear_delta + self.EPSILON >= clear_requirement:
            margin = clear_delta - clear_requirement
            return self._decision(
                best_discard,
                best_play,
                best_discard,
                clear_requirement,
                progress_requirement,
                clear_delta,
                progress_delta,
                self._confidence(margin),
                (
                    "discard improves projected clear probability enough to justify "
                    "spending a discard",
                ),
                len(plans),
            )

        below_play_floor = (
            play_value.clear_probability + self.EPSILON
            < self.thresholds.play_clear_probability_floor
        )
        if (
            below_play_floor
            and progress_delta + self.EPSILON >= progress_requirement
        ):
            margin = progress_delta - progress_requirement
            return self._decision(
                best_discard,
                best_play,
                best_discard,
                clear_requirement,
                progress_requirement,
                clear_delta,
                progress_delta,
                self._confidence(margin),
                (
                    "best play is below the D1 clear-probability floor",
                    "discard improves projected blind progress enough to justify redraw",
                ),
                len(plans),
            )

        rationale = []
        if play_value.clear_probability >= self.thresholds.play_clear_probability_floor:
            rationale.append("best play meets the D1 clear-probability floor")
        else:
            rationale.append("discard does not clear the required D1 advantage gates")
        if int(getattr(state, "discards_remaining", 0)) <= self.thresholds.low_discard_reserve:
            rationale.append("low discard reserve raises the evidence required to discard")
        if int(getattr(state, "hands_remaining", 0)) <= self.thresholds.low_hand_reserve:
            rationale.append("low hand reserve lowers the evidence required to preserve a hand")

        play_margin = max(
            clear_requirement - clear_delta,
            progress_requirement - progress_delta if below_play_floor else 0.0,
        )
        return self._decision(
            best_play,
            best_play,
            best_discard,
            clear_requirement,
            progress_requirement,
            clear_delta,
            progress_delta,
            self._confidence(play_margin),
            tuple(rationale),
            len(plans),
        )

    def _discard_requirements(self, state) -> tuple[float, float]:
        thresholds = self.thresholds
        clear_requirement = thresholds.discard_clear_probability_advantage
        progress_requirement = thresholds.discard_progress_advantage

        if int(getattr(state, "discards_remaining", 0)) <= thresholds.low_discard_reserve:
            clear_requirement += thresholds.low_discard_extra_clear_advantage
            progress_requirement += thresholds.low_discard_extra_progress_advantage

        if int(getattr(state, "hands_remaining", 0)) <= thresholds.low_hand_reserve:
            clear_requirement -= thresholds.low_hand_clear_advantage_discount
            progress_requirement -= thresholds.low_hand_progress_advantage_discount

        return max(0.0, clear_requirement), max(0.0, progress_requirement)

    @staticmethod
    def _within_type_key(plan: LiveBlindPlan) -> tuple[float, int, float, float, float, float]:
        value = plan.value
        return (
            value.clear_probability,
            1 if plan.exact else 0,
            value.expected_progress,
            value.expected_hands_remaining,
            value.expected_discards_remaining,
            value.expected_score,
        )

    @staticmethod
    def _confidence(margin: float) -> float:
        return max(0.0, min(1.0, 0.5 + max(0.0, margin) * 2.0))

    def _decision(
        self,
        selected: LiveBlindPlan,
        best_play: LiveBlindPlan,
        best_discard: LiveBlindPlan | None,
        required_clear: float,
        required_progress: float,
        clear_delta: float | None,
        progress_delta: float | None,
        confidence: float,
        rationale: tuple[str, ...],
        candidate_count: int,
    ) -> HandActionDecision:
        return HandActionDecision(
            action=selected.action,
            selected_plan=selected,
            best_play=best_play,
            best_discard=best_discard,
            thresholds=self.thresholds,
            required_discard_clear_advantage=required_clear,
            required_discard_progress_advantage=required_progress,
            clear_probability_delta=clear_delta,
            progress_delta=progress_delta,
            confidence=confidence,
            rationale=rationale,
            candidate_count=candidate_count,
        )


class LiveHandActionDecisionEngine:
    """Generate planner estimates, then apply the independent D1 threshold policy."""

    def __init__(
        self,
        *,
        planner: LiveBlindClearPlanner | None = None,
        policy: LiveHandActionThresholdPolicy | None = None,
    ) -> None:
        self.planner = planner or LiveBlindClearPlanner()
        self.policy = policy or LiveHandActionThresholdPolicy()

    def rank_plans(self, state) -> list[LiveBlindPlan]:
        planner = self.planner
        planner._require_state(state)
        planner.reset_search_stats()
        candidates = planner._candidate_actions(
            state,
            allow_discards=planner.horizon > 1,
        )
        if not candidates:
            raise RuntimeError("no D1 hand-action candidate is available")
        estimates = [
            planner._estimate_action(state, action, planner.horizon)
            for action in candidates
        ]
        estimates.sort(key=planner._estimate_key, reverse=True)
        return [
            LiveBlindPlan(
                action=estimate.action,
                value=estimate.value,
                horizon=planner.horizon,
                exact=estimate.exact,
                candidate_count=len(candidates),
            )
            for estimate in estimates
        ]

    def decide(self, state) -> HandActionDecision:
        plans = self.rank_plans(state)
        return self.policy.decide(state, plans)
