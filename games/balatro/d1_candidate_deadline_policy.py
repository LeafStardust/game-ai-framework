from __future__ import annotations

"""Apply the D1 wall-clock budget during root/child candidate ranking.

The canonical planner checked its deadline only when consuming a search node.  Root
candidate ranking happens before the first node and calls the expensive hand-score
projector once for every playable subset, so a nominal 8-second search could spend
minutes at nodes=0 before noticing that the deadline had expired.

This patch preserves the existing candidate semantics and ordering; it only inserts
wall-clock checks before and after each expensive priority evaluation and before
sorting/continuing to discard ranking.
"""

from time import perf_counter

from games.balatro.live.blind_clear_planner import (
    LiveBlindClearPlanner,
    PlannerSearchBudgetExceeded,
)


def _check_deadline(planner: LiveBlindClearPlanner, stage: str) -> None:
    deadline = getattr(planner, "deadline", None)
    if deadline is not None and perf_counter() >= float(deadline):
        raise PlannerSearchBudgetExceeded(
            f"live blind planner search exceeded wall-clock budget during {stage}"
        )


def _rank_with_deadline(planner, state, actions, *, key, limit: int, stage: str):
    scored = []
    for action in actions:
        _check_deadline(planner, stage)
        priority = key(state, action)
        _check_deadline(planner, stage)
        scored.append((priority, action))
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
        )

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
        )
        return ranked_plays + ranked_discards

    LiveBlindClearPlanner._candidate_actions = candidate_actions_with_deadline
    LiveBlindClearPlanner._candidate_deadline_installed = True
