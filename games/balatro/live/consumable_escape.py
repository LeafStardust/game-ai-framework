from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from itertools import combinations
from time import perf_counter

from games.balatro.live.blind_clear_planner import (
    LiveBlindClearPlanner,
    PlannerSearchBudgetExceeded,
)
from games.balatro.live.depth_draw_outcomes import DepthAwarePublicDrawOutcomeModel


@dataclass(frozen=True)
class SunEscapeRecommendation:
    consumable_index: int
    target_indices: tuple[int, ...]
    plan: object
    targets_considered: int
    targets_searched: int
    targets_budget_exceeded: int
    nodes_evaluated: int

    @property
    def clear_probability(self) -> float:
        return float(self.plan.value.clear_probability)

    @property
    def expected_score(self) -> float:
        return float(self.plan.value.expected_score)

    @property
    def exact(self) -> bool:
        return bool(self.plan.exact)

    @property
    def guaranteed_clear(self) -> bool:
        return bool(self.exact and self.clear_probability >= 1.0 - 1e-12)


class SunConsumableEscapePlanner:
    """Plan one deterministic The Sun use before normal blind play.

    Only public state is used. The Sun changes the suit of one to three selected
    hand cards to Hearts and consumes no hand/discard. Candidate target sets are
    first ranked by a cheap one-play search, then the best few are evaluated by
    the configured multi-action blind planner. Hidden draw order is never used.
    """

    def __init__(
        self,
        *,
        horizon: int,
        exact_combination_limit: int = LiveBlindClearPlanner.DEFAULT_EXACT_DRAW_COMBINATION_LIMIT,
        root_sample_count: int = 8,
        child_sample_count: int = 2,
        child_exact_combination_limit: int | None = None,
        play_width: int = 6,
        discard_width: int = 1,
        child_play_width: int = 2,
        child_discard_width: int = 1,
        max_nodes: int = 10000,
        target_width: int = 16,
        deadline: float | None = None,
    ):
        if horizon < 1:
            raise ValueError("horizon must be positive")
        if target_width < 1:
            raise ValueError("target_width must be positive")
        self.horizon = int(horizon)
        self.exact_combination_limit = int(exact_combination_limit)
        self.root_sample_count = int(root_sample_count)
        self.child_sample_count = int(child_sample_count)
        self.child_exact_combination_limit = child_exact_combination_limit
        self.play_width = int(play_width)
        self.discard_width = int(discard_width)
        self.child_play_width = int(child_play_width)
        self.child_discard_width = int(child_discard_width)
        self.max_nodes = int(max_nodes)
        self.target_width = int(target_width)
        self.deadline = float(deadline) if deadline is not None else None

    def _check_deadline(self) -> None:
        if self.deadline is not None and perf_counter() >= self.deadline:
            raise PlannerSearchBudgetExceeded(
                "The Sun escape planner exceeded the parent D1 wall-clock budget"
            )

    def plan(self, state) -> SunEscapeRecommendation:
        self._check_deadline()
        sun_index = self._sun_index(state)
        if sun_index is None:
            raise RuntimeError("The Sun is not held")
        if getattr(state, "phase", None) != "SELECTING_HAND":
            raise RuntimeError("The Sun escape planner requires SELECTING_HAND")
        if not getattr(state, "hand", None):
            raise RuntimeError("The Sun escape planner requires a non-empty hand")

        targets = self._target_sets(state)
        if not targets:
            raise RuntimeError("The Sun has no meaningful current-hand target")

        ranked = []
        for indices in targets:
            self._check_deadline()
            transformed = self._apply_sun(state, indices, sun_index)
            preview = self._planner(
                horizon=1,
                play_width=max(self.play_width, 6),
                discard_width=0,
                child_play_width=1,
                child_discard_width=0,
                max_nodes=min(self.max_nodes, 2000),
            )
            try:
                plan = preview.plan(transformed)
            except PlannerSearchBudgetExceeded:
                continue
            ranked.append((self._plan_key(plan, indices), indices))

        if not ranked:
            raise RuntimeError("every The Sun target preview exceeded its node budget")

        ranked.sort(reverse=True)
        shortlisted = [indices for _, indices in ranked[: self.target_width]]

        best = None
        best_indices = None
        total_nodes = 0
        budget_exceeded = 0
        searched = 0

        for indices in shortlisted:
            self._check_deadline()
            transformed = self._apply_sun(state, indices, sun_index)
            planner = self._planner(
                horizon=self.horizon,
                play_width=self.play_width,
                discard_width=(self.discard_width if state.discards_remaining > 0 else 0),
                child_play_width=self.child_play_width,
                child_discard_width=(
                    self.child_discard_width if state.discards_remaining > 0 else 0
                ),
                max_nodes=self.max_nodes,
            )
            unsupported = planner.evaluator.score_outcomes.joker_projector.unsupported_jokers(
                transformed
            )
            if unsupported:
                raise RuntimeError(
                    "The Sun escape planner is blocked by unsupported Joker projection(s): "
                    + ", ".join(unsupported)
                )
            try:
                plan = planner.plan(transformed)
            except PlannerSearchBudgetExceeded:
                budget_exceeded += 1
                total_nodes += planner.nodes_evaluated
                continue
            searched += 1
            total_nodes += planner.nodes_evaluated
            if best is None or self._plan_key(plan, indices) > self._plan_key(
                best, best_indices
            ):
                best = plan
                best_indices = indices

        if best is None or best_indices is None:
            raise RuntimeError("every shortlisted The Sun target exceeded its node budget")

        return SunEscapeRecommendation(
            consumable_index=sun_index,
            target_indices=best_indices,
            plan=best,
            targets_considered=len(targets),
            targets_searched=searched,
            targets_budget_exceeded=budget_exceeded,
            nodes_evaluated=total_nodes,
        )

    def _planner(
        self,
        *,
        horizon: int,
        play_width: int,
        discard_width: int,
        child_play_width: int,
        child_discard_width: int,
        max_nodes: int,
    ) -> LiveBlindClearPlanner:
        return LiveBlindClearPlanner(
            draw_outcomes=DepthAwarePublicDrawOutcomeModel(
                exact_combination_limit=self.exact_combination_limit,
                root_sample_count=self.root_sample_count,
                child_sample_count=self.child_sample_count,
                child_exact_combination_limit=self.child_exact_combination_limit,
            ),
            play_width=play_width,
            discard_width=discard_width,
            child_play_width=child_play_width,
            child_discard_width=child_discard_width,
            horizon=horizon,
            max_nodes=max_nodes,
            deadline=self.deadline,
        )

    @staticmethod
    def _sun_index(state) -> int | None:
        for index, consumable in enumerate(getattr(state, "consumables", ())):
            if getattr(consumable, "name", None) == "The Sun":
                return index
        return None

    @staticmethod
    def _target_sets(state) -> tuple[tuple[int, ...], ...]:
        eligible = [
            index
            for index, card in enumerate(state.hand)
            if getattr(card, "suit", None) != "Hearts"
            and not bool(getattr(card, "is_wild", False))
            and not bool(getattr(card, "is_stone", False))
        ]
        return tuple(
            tuple(indices)
            for size in range(1, min(3, len(eligible)) + 1)
            for indices in combinations(eligible, size)
        )

    @staticmethod
    def _apply_sun(state, indices: tuple[int, ...], sun_index: int):
        transformed = deepcopy(state)
        for index in indices:
            transformed.hand[index].suit = "Hearts"
        if 0 <= sun_index < len(transformed.consumables):
            transformed.consumables.pop(sun_index)
        return transformed

    @staticmethod
    def _plan_key(plan, indices: tuple[int, ...] | None) -> tuple:
        target_count = len(indices or ())
        return (
            1 if plan.exact and plan.value.clear_probability >= 1.0 - 1e-12 else 0,
            float(plan.value.clear_probability),
            float(plan.value.expected_score),
            float(plan.value.expected_hands_remaining),
            float(plan.value.expected_discards_remaining),
            -target_count,
            tuple(-(index) for index in (indices or ())),
        )


def judgement_live_block_reason(state) -> str | None:
    if not any(
        getattr(consumable, "name", None) == "Judgement"
        for consumable in getattr(state, "consumables", ())
    ):
        return None
    return (
        "Judgement is held but live blind planning is blocked for it: the created "
        "Joker is random and the live scorer does not yet support the full Joker pool"
    )
