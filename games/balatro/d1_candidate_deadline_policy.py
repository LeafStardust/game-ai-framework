from __future__ import annotations

"""Apply D1 wall-clock budgets during root/child candidate ranking.

The canonical planner checked its deadline only when consuming a search node. Root
candidate ranking happens before the first node and calls the expensive hand-score
projector once for every playable subset, so a nominal search budget could be spent
before any usable root plan existed.

The normal hard deadline remains authoritative. At the initial root only, candidate
ranking also has a short soft bootstrap envelope: once at least one candidate has
been scored, the planner may stop expanding that beam and proceed with the best
bounded candidates already seen. Child ranking and later completed-pass refinement
retain the ordinary configured search budget.
"""

from time import perf_counter

from games.balatro.live.blind_clear_planner import (
    LiveBlindClearPlanner,
    PlannerSearchBudgetExceeded,
)


ROOT_BOOTSTRAP_SECONDS = 0.75


def _check_deadline(planner: LiveBlindClearPlanner, stage: str) -> None:
    deadline = getattr(planner, "deadline", None)
    if deadline is not None and perf_counter() >= float(deadline):
        raise PlannerSearchBudgetExceeded(
            f"live blind planner search exceeded wall-clock budget during {stage}"
        )


def _rank_with_deadline(
    planner,
    state,
    actions,
    *,
    key,
    limit: int,
    stage: str,
    soft_deadline: float | None = None,
):
    scored = []
    for action in actions:
        _check_deadline(planner, stage)
        if soft_deadline is not None and scored and perf_counter() >= soft_deadline:
            break
        priority = key(state, action)
        _check_deadline(planner, stage)
        scored.append((priority, action))
        if soft_deadline is not None and perf_counter() >= soft_deadline:
            break
    _check_deadline(planner, stage)
    scored.sort(key=lambda item: item[0], reverse=True)
    return [action for _, action in scored[:limit]]


def install_d1_candidate_deadline_policy() -> None:
    if getattr(LiveBlindClearPlanner, "_candidate_deadline_installed", False):
        return

    def candidate_actions_with_deadline(
        self,
        state,
        *,
        allow_discards: bool,
        play_width: int | None = None,
        discard_width: int | None = None,
    ):
        play_limit = self.play_width if play_width is None else int(play_width)
        discard_limit = self.discard_width if discard_width is None else int(discard_width)

        initial_root = int(getattr(self, "nodes_evaluated", 0)) == 0
        soft_deadline = None
        if initial_root:
            soft_deadline = perf_counter() + ROOT_BOOTSTRAP_SECONDS
            hard_deadline = getattr(self, "deadline", None)
            if hard_deadline is not None:
                soft_deadline = min(float(hard_deadline), soft_deadline)

        _check_deadline(self, "play candidate generation")
        plays = self.action_generator.generate_play_actions(state)
        _check_deadline(self, "play candidate generation")
        ranked_plays = _rank_with_deadline(
            self,
            state,
            plays,
            key=self._play_priority,
            limit=play_limit,
            stage="play candidate ranking",
            soft_deadline=soft_deadline,
        )

        # A root bootstrap that has already consumed its soft envelope should start
        # evaluating the usable Play beam immediately instead of spending another
        # root pass ranking Discards before any plan exists.
        if initial_root and soft_deadline is not None and perf_counter() >= soft_deadline:
            return ranked_plays

        if (
            not allow_discards
            or discard_limit <= 0
            or int(getattr(state, "discards_remaining", 0)) <= 0
        ):
            return ranked_plays

        _check_deadline(self, "discard candidate generation")
        discards = self.action_generator.generate_discard_actions(state)
        _check_deadline(self, "discard candidate generation")
        ranked_discards = _rank_with_deadline(
            self,
            state,
            discards,
            key=self._discard_priority,
            limit=discard_limit,
            stage="discard candidate ranking",
            soft_deadline=soft_deadline if initial_root else None,
        )
        return ranked_plays + ranked_discards

    LiveBlindClearPlanner._candidate_actions = candidate_actions_with_deadline
    LiveBlindClearPlanner._candidate_deadline_installed = True
