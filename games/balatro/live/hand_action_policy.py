from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Mapping

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.live.adaptive_search import (
    AdaptiveBlindSearchConfig,
    AdaptiveRecommendationSummary,
    adaptive_blind_search_schedule,
    stable_discard_consensus,
)
from games.balatro.live.blind_clear_planner import (
    LiveBlindClearPlanner,
    LiveBlindPlan,
    PlannerSearchBudgetExceeded,
)
from games.balatro.live.depth_draw_outcomes import DepthAwarePublicDrawOutcomeModel
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.live.hand_decision import LiveHandDecisionEvaluator


CLEAR_PATH = "CLEAR_PATH"
PACE_PLAY = "PACE_PLAY"
PACE_RECOVERY = "PACE_RECOVERY"


@dataclass(frozen=True)
class HandActionThresholds:
    """Thresholds owned only by D1: hand play/discard decisions.

    D1 is hierarchical. A sufficiently credible blind-clear path always takes
    precedence. The pace thresholds are consulted only when adaptive clear-path
    search cannot find such a path.
    """

    clear_path_probability_floor: float = 0.75
    pace_ratio_floor: float = 1.0
    setup_discard_consensus_agreement: int = 3
    low_discard_reserve: int = 1
    low_discard_fallback_penalty: float = 10.0
    low_hand_reserve: int = 1
    low_hand_discard_fallback_bonus: float = 10.0

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.clear_path_probability_floor) <= 1.0:
            raise ValueError("clear_path_probability_floor must be between 0 and 1")
        if float(self.pace_ratio_floor) <= 0.0:
            raise ValueError("pace_ratio_floor must be positive")
        if self.setup_discard_consensus_agreement < 2:
            raise ValueError("setup_discard_consensus_agreement must be at least 2")
        if self.low_discard_reserve < 0:
            raise ValueError("low_discard_reserve cannot be negative")
        if self.low_hand_reserve < 0:
            raise ValueError("low_hand_reserve cannot be negative")
        if float(self.low_discard_fallback_penalty) < 0.0:
            raise ValueError("low_discard_fallback_penalty cannot be negative")
        if float(self.low_hand_discard_fallback_bonus) < 0.0:
            raise ValueError("low_hand_discard_fallback_bonus cannot be negative")

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
class HandActionSearchAttempt:
    horizon: int
    samples: int
    play_width: int
    discard_width: int
    max_nodes: int
    nodes_evaluated: int
    budget_exceeded: bool
    confirmation: bool = False
    best_action: str | None = None
    best_clear_probability: float | None = None
    best_expected_score: float | None = None
    best_exact: bool | None = None


@dataclass(frozen=True)
class HandActionDecision:
    mode: str
    action: BalatroAction
    selected_plan: LiveBlindPlan
    best_play: LiveBlindPlan
    best_discard: LiveBlindPlan | None
    thresholds: HandActionThresholds
    pace_target: float
    best_play_immediate_score: float
    best_play_pace_ratio: float
    selected_immediate_score: float | None
    selected_pace_ratio: float | None
    selected_fallback_value: float | None
    clear_path_candidates: int
    sampled_clear_path_confirmed: bool
    setup_discard_consensus: bool
    confidence: float
    rationale: tuple[str, ...]
    candidate_count: int
    plans: tuple[LiveBlindPlan, ...]
    search_attempts: tuple[HandActionSearchAttempt, ...] = ()


class LiveHandActionPolicy:
    """D1 hierarchy: credible clear path first, then next-hand pace fallback.

    CLEAR_PATH:
        Exact probability evidence may be accepted immediately. A sampled/inexact
        path must be independently confirmed by the decision engine with a stronger
        same-horizon sampling pass before this policy will tunnel into it.

    PACE_PLAY:
        If no credible clear path exists but a current play can meet the required
        next-hand pace, play a pace-satisfying subset.

    PACE_RECOVERY:
        If no current play can meet pace, use the pace-aware evaluator to choose
        the best recovery action. This may be a setup discard or, when a discard
        is not worthwhile/legal, the strongest available under-pace play.
    """

    EPSILON = 1e-12
    SAMPLED_CONFIDENCE_CAP = 0.95

    def __init__(
        self,
        thresholds: HandActionThresholds | None = None,
        *,
        evaluator: LiveHandDecisionEvaluator | None = None,
    ) -> None:
        self.thresholds = thresholds or HandActionThresholds()
        self.evaluator = evaluator or LiveHandDecisionEvaluator()

    def decide(
        self,
        state,
        plans: list[LiveBlindPlan] | tuple[LiveBlindPlan, ...],
        *,
        search_attempts: tuple[HandActionSearchAttempt, ...] = (),
        confirmed_clear_path: LiveBlindPlan | None = None,
        setup_discard_consensus: bool = False,
    ) -> HandActionDecision:
        plans = tuple(plans)
        plays = [plan for plan in plans if plan.action.name == PLAY_CARDS]
        discards = [plan for plan in plans if plan.action.name == DISCARD_CARDS]
        if not plays:
            raise ValueError("D1 requires at least one PLAY_CARDS candidate")

        best_play = max(plays, key=self._within_type_key)
        best_discard = max(discards, key=self._within_type_key) if discards else None
        pace_target = self._pace_target(state)
        immediate_scores = {
            id(plan): float(self.evaluator.project_play(state, plan.action).expected_hand_score)
            for plan in plays
        }
        best_immediate_play = max(plays, key=lambda plan: immediate_scores[id(plan)])
        best_immediate_score = immediate_scores[id(best_immediate_play)]
        best_immediate_ratio = self._pace_ratio(best_immediate_score, pace_target)

        credible_clear_paths = [
            plan
            for plan in plans
            if plan.exact and self._meets_clear_floor(plan)
        ]
        sampled_confirmed = False
        if confirmed_clear_path is not None:
            if confirmed_clear_path not in plans:
                raise ValueError("confirmed D1 clear path must belong to the supplied plans")
            if not self._meets_clear_floor(confirmed_clear_path):
                raise ValueError("confirmed D1 clear path is below the probability floor")
            if not confirmed_clear_path.exact:
                sampled_confirmed = True
            credible_clear_paths.append(confirmed_clear_path)

        if credible_clear_paths:
            selected = max(credible_clear_paths, key=self._within_type_key)
            selected_score = None
            selected_ratio = None
            if selected.action.name == PLAY_CARDS:
                selected_score = immediate_scores[id(selected)]
                selected_ratio = self._pace_ratio(selected_score, pace_target)
            probability = float(selected.value.clear_probability)
            selected_is_confirmed_sample = sampled_confirmed and selected is confirmed_clear_path
            confidence = probability
            if selected_is_confirmed_sample:
                confidence = min(confidence, self.SAMPLED_CONFIDENCE_CAP)

            rationale = [
                "credible blind-clear path meets the D1 probability floor",
            ]
            if selected_is_confirmed_sample:
                rationale.append(
                    "sampled path kept the same first action in a stronger same-horizon confirmation pass"
                )
            elif selected.exact:
                rationale.append("clear-path probability was evaluated exactly")
            rationale.append(
                "take only the first action, then re-observe and replan from the real checkpoint"
            )
            return self._decision(
                mode=CLEAR_PATH,
                selected=selected,
                best_play=best_play,
                best_discard=best_discard,
                pace_target=pace_target,
                best_play_immediate_score=best_immediate_score,
                best_play_pace_ratio=best_immediate_ratio,
                selected_immediate_score=selected_score,
                selected_pace_ratio=selected_ratio,
                selected_fallback_value=None,
                clear_path_candidates=len(credible_clear_paths),
                sampled_clear_path_confirmed=selected_is_confirmed_sample,
                setup_discard_consensus=setup_discard_consensus,
                confidence=confidence,
                rationale=tuple(rationale),
                plans=plans,
                search_attempts=search_attempts,
            )

        pace_plays = [
            plan
            for plan in plays
            if self._pace_ratio(immediate_scores[id(plan)], pace_target) + self.EPSILON
            >= self.thresholds.pace_ratio_floor
        ]
        if pace_plays:
            selected = max(
                pace_plays,
                key=lambda plan: self._pace_play_key(
                    plan,
                    self._pace_ratio(immediate_scores[id(plan)], pace_target),
                ),
            )
            selected_score = immediate_scores[id(selected)]
            selected_ratio = self._pace_ratio(selected_score, pace_target)
            confidence = self._pace_confidence(selected_ratio)
            return self._decision(
                mode=PACE_PLAY,
                selected=selected,
                best_play=best_play,
                best_discard=best_discard,
                pace_target=pace_target,
                best_play_immediate_score=best_immediate_score,
                best_play_pace_ratio=best_immediate_ratio,
                selected_immediate_score=selected_score,
                selected_pace_ratio=selected_ratio,
                selected_fallback_value=None,
                clear_path_candidates=0,
                sampled_clear_path_confirmed=False,
                setup_discard_consensus=setup_discard_consensus,
                confidence=confidence,
                rationale=(
                    "adaptive search found no credible blind-clear path",
                    "a current play can meet the required next-hand pace",
                ),
                plans=plans,
                search_attempts=search_attempts,
            )

        scored = []
        for plan in plans:
            value = float(self.evaluator.evaluate(state, plan.action))
            if plan.action.name == DISCARD_CARDS:
                if (
                    int(getattr(state, "discards_remaining", 0))
                    <= self.thresholds.low_discard_reserve
                ):
                    value -= self.thresholds.low_discard_fallback_penalty
                if (
                    int(getattr(state, "hands_remaining", 0))
                    <= self.thresholds.low_hand_reserve
                ):
                    value += self.thresholds.low_hand_discard_fallback_bonus
            scored.append((value, plan))

        scored.sort(
            key=lambda item: (item[0], self._within_type_key(item[1])),
            reverse=True,
        )
        selected_value, selected = scored[0]
        selected_score = None
        selected_ratio = None
        if selected.action.name == PLAY_CARDS:
            selected_score = immediate_scores[id(selected)]
            selected_ratio = self._pace_ratio(selected_score, pace_target)

        runner_up = scored[1][0] if len(scored) > 1 else selected_value
        confidence = self._recovery_confidence(
            selected_value - runner_up,
            consensus=(
                setup_discard_consensus and selected.action.name == DISCARD_CARDS
            ),
        )
        rationale = [
            "adaptive search found no credible blind-clear path",
            "no current play reaches the required next-hand pace",
        ]
        if selected.action.name == DISCARD_CARDS:
            rationale.append("pace-aware recovery prefers a setup discard")
            if setup_discard_consensus:
                rationale.append("deep adaptive searches also agree on the setup discard")
            if (
                int(getattr(state, "discards_remaining", 0))
                <= self.thresholds.low_discard_reserve
            ):
                rationale.append("low discard reserve penalty was applied")
        else:
            rationale.append("discard recovery is not better than the strongest under-pace play")

        return self._decision(
            mode=PACE_RECOVERY,
            selected=selected,
            best_play=best_play,
            best_discard=best_discard,
            pace_target=pace_target,
            best_play_immediate_score=best_immediate_score,
            best_play_pace_ratio=best_immediate_ratio,
            selected_immediate_score=selected_score,
            selected_pace_ratio=selected_ratio,
            selected_fallback_value=selected_value,
            clear_path_candidates=0,
            sampled_clear_path_confirmed=False,
            setup_discard_consensus=setup_discard_consensus,
            confidence=confidence,
            rationale=tuple(rationale),
            plans=plans,
            search_attempts=search_attempts,
        )

    def best_clear_path(
        self,
        plans: list[LiveBlindPlan] | tuple[LiveBlindPlan, ...],
        *,
        exact_only: bool = False,
    ) -> LiveBlindPlan | None:
        candidates = [
            plan
            for plan in plans
            if self._meets_clear_floor(plan) and (plan.exact or not exact_only)
        ]
        return max(candidates, key=self._within_type_key) if candidates else None

    def _meets_clear_floor(self, plan: LiveBlindPlan) -> bool:
        return (
            float(plan.value.clear_probability) + self.EPSILON
            >= self.thresholds.clear_path_probability_floor
        )

    @staticmethod
    def _pace_target(state) -> float:
        target = float(getattr(getattr(state, "blind", None), "requirement", 0))
        current = float(getattr(state, "score", 0))
        remaining = max(0.0, target - current)
        hands = max(1, int(getattr(state, "hands_remaining", 0)))
        return remaining / hands

    @staticmethod
    def _pace_ratio(score: float, target: float) -> float:
        if target <= 1e-12:
            return 1.0
        return float(score) / float(target)

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

    def _pace_play_key(
        self,
        plan: LiveBlindPlan,
        pace_ratio: float,
    ) -> tuple[float, int, float, float, float, float]:
        value = plan.value
        return (
            value.clear_probability,
            1 if plan.exact else 0,
            value.expected_progress,
            value.expected_discards_remaining,
            value.expected_hands_remaining,
            -abs(pace_ratio - self.thresholds.pace_ratio_floor),
        )

    def _pace_confidence(self, ratio: float) -> float:
        margin = max(0.0, ratio - self.thresholds.pace_ratio_floor)
        return max(0.5, min(1.0, 0.75 + margin * 0.25))

    @staticmethod
    def _recovery_confidence(margin: float, *, consensus: bool) -> float:
        base = 0.65 if consensus else 0.40
        return max(base, min(1.0, base + max(0.0, margin) / 200.0))

    def _decision(
        self,
        *,
        mode: str,
        selected: LiveBlindPlan,
        best_play: LiveBlindPlan,
        best_discard: LiveBlindPlan | None,
        pace_target: float,
        best_play_immediate_score: float,
        best_play_pace_ratio: float,
        selected_immediate_score: float | None,
        selected_pace_ratio: float | None,
        selected_fallback_value: float | None,
        clear_path_candidates: int,
        sampled_clear_path_confirmed: bool,
        setup_discard_consensus: bool,
        confidence: float,
        rationale: tuple[str, ...],
        plans: tuple[LiveBlindPlan, ...],
        search_attempts: tuple[HandActionSearchAttempt, ...],
    ) -> HandActionDecision:
        return HandActionDecision(
            mode=mode,
            action=selected.action,
            selected_plan=selected,
            best_play=best_play,
            best_discard=best_discard,
            thresholds=self.thresholds,
            pace_target=pace_target,
            best_play_immediate_score=best_play_immediate_score,
            best_play_pace_ratio=best_play_pace_ratio,
            selected_immediate_score=selected_immediate_score,
            selected_pace_ratio=selected_pace_ratio,
            selected_fallback_value=selected_fallback_value,
            clear_path_candidates=clear_path_candidates,
            sampled_clear_path_confirmed=sampled_clear_path_confirmed,
            setup_discard_consensus=setup_discard_consensus,
            confidence=confidence,
            rationale=rationale,
            candidate_count=len(plans),
            plans=plans,
            search_attempts=search_attempts,
        )


# Compatibility name for older imports while D1 callers migrate to the clearer name.
LiveHandActionThresholdPolicy = LiveHandActionPolicy


class LiveHandActionDecisionEngine:
    """Adaptive D1 search followed by the pace fallback hierarchy."""

    CONFIRMATION_MIN_ROOT_SAMPLES = 32
    CONFIRMATION_MIN_CHILD_SAMPLES = 4
    CONFIRMATION_MAX_NODES = 1000

    def __init__(
        self,
        *,
        planner: LiveBlindClearPlanner | None = None,
        policy: LiveHandActionPolicy | None = None,
        max_horizon: int = 8,
        max_search_nodes: int = 5000,
        exact_limit: int = LiveBlindClearPlanner.DEFAULT_EXACT_DRAW_COMBINATION_LIMIT,
        child_exact_limit: int = 8,
    ) -> None:
        if max_horizon < 1:
            raise ValueError("max_horizon must be positive")
        if max_search_nodes < 1:
            raise ValueError("max_search_nodes must be positive")
        if exact_limit < 1:
            raise ValueError("exact_limit must be positive")
        if child_exact_limit < 1:
            raise ValueError("child_exact_limit must be positive")

        self.planner = planner or D1LiveBlindClearPlanner(
            play_width=6,
            discard_width=4,
            child_play_width=4,
            child_discard_width=2,
            horizon=2,
            max_nodes=3000,
        )
        self.policy = policy or LiveHandActionPolicy(evaluator=self.planner.evaluator)
        self.max_horizon = int(max_horizon)
        self.max_search_nodes = int(max_search_nodes)
        self.exact_limit = int(exact_limit)
        self.child_exact_limit = int(child_exact_limit)

    def rank_plans(
        self,
        state,
        *,
        planner: LiveBlindClearPlanner | None = None,
    ) -> list[LiveBlindPlan]:
        planner = planner or self.planner
        planner._require_state(state)
        planner.reset_search_stats()
        root_action = getattr(planner, "_confirmation_root_action", None)
        candidates = (
            [root_action]
            if root_action is not None
            else planner._candidate_actions(
                state,
                allow_discards=planner.horizon > 1,
            )
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

    def _rank_immediate_plans(self, state) -> list[LiveBlindPlan]:
        """Rank a bounded one-action fallback from only the current public state.

        This path is used after adaptive clear-path search has exhausted its useful
        horizon. Depth one cannot recurse into draw outcomes, while explicitly
        retaining legal discard candidates keeps the pace-recovery hierarchy intact.
        """
        planner = self.planner
        planner._require_state(state)
        planner.reset_search_stats()
        candidates = planner._candidate_actions(state, allow_discards=True)
        if not candidates:
            raise RuntimeError("no immediate D1 fallback candidate is available")
        estimates = [planner._estimate_action(state, action, 1) for action in candidates]
        estimates.sort(key=planner._estimate_key, reverse=True)
        return [
            LiveBlindPlan(
                action=estimate.action,
                value=estimate.value,
                horizon=1,
                exact=estimate.exact,
                candidate_count=len(candidates),
            )
            for estimate in estimates
        ]

    def decide(self, state) -> HandActionDecision:
        schedule = adaptive_blind_search_schedule(
            hands_remaining=int(getattr(state, "hands_remaining", 0)),
            discards_remaining=int(getattr(state, "discards_remaining", 0)),
            max_horizon=self.max_horizon,
            max_nodes=self.max_search_nodes,
        )
        attempts: list[HandActionSearchAttempt] = []
        summaries: list[AdaptiveRecommendationSummary] = []

        for config in schedule:
            planner = self._adaptive_planner(config)
            try:
                plans = self.rank_plans(state, planner=planner)
            except PlannerSearchBudgetExceeded:
                attempts.append(self._attempt(config, planner, confirmation=False))
                continue

            best = plans[0]
            attempts.append(
                self._attempt(
                    config,
                    planner,
                    confirmation=False,
                    best=best,
                )
            )
            summaries.append(
                AdaptiveRecommendationSummary(
                    action=best.action.name,
                    indices=self._indices(state, best.action),
                    clear_probability=float(best.value.clear_probability),
                    expected_score=float(best.value.expected_score),
                    horizon=config.horizon,
                    intensified=config.max_nodes > 5000,
                )
            )

            clear_path = self.policy.best_clear_path(plans)
            if clear_path is None:
                continue

            if clear_path.exact:
                return self.policy.decide(
                    state,
                    plans,
                    search_attempts=tuple(attempts),
                    setup_discard_consensus=False,
                )

            confirmation_config = self._confirmation_config(config)
            confirmation_planner = self._adaptive_planner(confirmation_config)
            try:
                confirmed = self._confirm_plan(
                    state,
                    clear_path,
                    planner=confirmation_planner,
                )
            except PlannerSearchBudgetExceeded:
                attempts.append(
                    self._attempt(
                        confirmation_config,
                        confirmation_planner,
                        confirmation=True,
                    )
                )
                continue

            attempts.append(
                self._attempt(
                    confirmation_config,
                    confirmation_planner,
                    confirmation=True,
                    best=confirmed,
                )
            )

            if self._action_signature(state, confirmed.action) != self._action_signature(
                state,
                clear_path.action,
            ):
                continue
            if not self.policy._meets_clear_floor(confirmed):
                continue

            confirmed_plans = self._replace_matching_plan(
                state,
                plans,
                clear_path,
                confirmed,
            )
            if confirmed.exact:
                return self.policy.decide(
                    state,
                    confirmed_plans,
                    search_attempts=tuple(attempts),
                    setup_discard_consensus=False,
                )
            return self.policy.decide(
                state,
                confirmed_plans,
                search_attempts=tuple(attempts),
                confirmed_clear_path=confirmed,
                setup_discard_consensus=False,
            )

        consensus = stable_discard_consensus(
            tuple(summaries),
            minimum_agreement=self.policy.thresholds.setup_discard_consensus_agreement,
        )

        # No credible adaptive search survived the exact/sampled confirmation gate.
        # Pace/recovery needs broad current-action coverage, not another recursive
        # draw search. Go directly to the bounded one-action beam so autonomy cannot
        # spend a second search budget re-proving that no clear path was confirmed.
        fallback_plans = self._rank_immediate_plans(state)
        return self.policy.decide(
            state,
            fallback_plans,
            search_attempts=tuple(attempts),
            setup_discard_consensus=consensus,
        )

    def _confirm_plan(
        self,
        state,
        original: LiveBlindPlan,
        *,
        planner: LiveBlindClearPlanner,
    ) -> LiveBlindPlan:
        """Re-evaluate only the sampled first action under stronger sampling.

        Confirmation is not a second root policy search. Its purpose is to ask
        whether the exact same first action survives a stronger same-horizon
        public-state estimate. Recursive continuations remain fully searched by
        the confirmation planner; only redundant root action enumeration is
        removed.
        """
        setattr(planner, "_confirmation_root_action", original.action)
        try:
            plans = self.rank_plans(state, planner=planner)
        finally:
            try:
                delattr(planner, "_confirmation_root_action")
            except AttributeError:
                pass
        if not plans:
            raise RuntimeError("D1 confirmation produced no plan")
        return plans[0]

    def _replace_matching_plan(
        self,
        state,
        plans: list[LiveBlindPlan] | tuple[LiveBlindPlan, ...],
        original: LiveBlindPlan,
        confirmed: LiveBlindPlan,
    ) -> list[LiveBlindPlan]:
        signature = self._action_signature(state, original.action)
        replaced = []
        matched = False
        for plan in plans:
            if self._action_signature(state, plan.action) == signature:
                replaced.append(confirmed)
                matched = True
            else:
                replaced.append(plan)
        if not matched:
            raise RuntimeError("confirmed D1 first action is missing from root plans")
        return replaced

    def _adaptive_planner(self, config: AdaptiveBlindSearchConfig) -> D1LiveBlindClearPlanner:
        return D1LiveBlindClearPlanner(
            evaluator=self.planner.evaluator,
            action_generator=self.planner.action_generator,
            draw_outcomes=DepthAwarePublicDrawOutcomeModel(
                exact_combination_limit=self.exact_limit,
                root_sample_count=config.samples,
                child_sample_count=config.child_samples,
                child_exact_combination_limit=self.child_exact_limit,
            ),
            play_width=config.play_width,
            discard_width=config.discard_width,
            child_play_width=config.child_play_width,
            child_discard_width=config.child_discard_width,
            horizon=config.horizon,
            max_nodes=config.max_nodes,
        )

    def _confirmation_config(
        self,
        config: AdaptiveBlindSearchConfig,
    ) -> AdaptiveBlindSearchConfig:
        return AdaptiveBlindSearchConfig(
            horizon=config.horizon,
            samples=max(self.CONFIRMATION_MIN_ROOT_SAMPLES, config.samples * 4),
            child_samples=max(
                self.CONFIRMATION_MIN_CHILD_SAMPLES,
                config.child_samples * 4,
            ),
            play_width=config.play_width,
            discard_width=config.discard_width,
            child_play_width=config.child_play_width,
            child_discard_width=config.child_discard_width,
            max_nodes=min(config.max_nodes, self.CONFIRMATION_MAX_NODES),
        )

    def _matching_clear_path(
        self,
        state,
        original: LiveBlindPlan,
        confirmation_plans: list[LiveBlindPlan] | tuple[LiveBlindPlan, ...],
    ) -> LiveBlindPlan | None:
        original_signature = self._action_signature(state, original.action)
        candidates = [
            plan
            for plan in confirmation_plans
            if self.policy._meets_clear_floor(plan)
            and self._action_signature(state, plan.action) == original_signature
        ]
        if not candidates:
            return None
        return max(candidates, key=self.policy._within_type_key)

    @staticmethod
    def _attempt(
        config: AdaptiveBlindSearchConfig,
        planner: LiveBlindClearPlanner,
        *,
        confirmation: bool,
        best: LiveBlindPlan | None = None,
    ) -> HandActionSearchAttempt:
        return HandActionSearchAttempt(
            horizon=config.horizon,
            samples=config.samples,
            play_width=config.play_width,
            discard_width=config.discard_width,
            max_nodes=config.max_nodes,
            nodes_evaluated=planner.nodes_evaluated,
            budget_exceeded=(best is None),
            confirmation=confirmation,
            best_action=best.action.name if best is not None else None,
            best_clear_probability=(
                float(best.value.clear_probability) if best is not None else None
            ),
            best_expected_score=(
                float(best.value.expected_score) if best is not None else None
            ),
            best_exact=best.exact if best is not None else None,
        )

    def _action_signature(self, state, action) -> tuple[str, tuple[int, ...]]:
        return action.name, self._indices(state, action)

    @staticmethod
    def _indices(state, action) -> tuple[int, ...]:
        selected_ids = {id(card) for card in action.cards}
        return tuple(
            index
            for index, card in enumerate(state.hand)
            if id(card) in selected_ids
        )
