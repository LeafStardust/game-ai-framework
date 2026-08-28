from __future__ import annotations

"""Compatibility surface for the former D1 candidate-deadline monkeypatch.

Candidate-generation hard deadline checks and the bounded initial-root bootstrap now
live directly in ``LiveBlindClearPlanner``. This module must not install a second
``_candidate_actions`` authority, but it retains the former helper names so older
imports/tests do not fail while the repository converges on the canonical planner.
"""

from time import perf_counter

from games.balatro.live.blind_clear_planner import (
    LiveBlindClearPlanner,
    PlannerSearchBudgetExceeded,
)


ROOT_BOOTSTRAP_SECONDS = LiveBlindClearPlanner.ROOT_CANDIDATE_BOOTSTRAP_SECONDS


def _check_deadline(planner: LiveBlindClearPlanner, stage: str = "candidate ranking") -> None:
    """Compatibility helper matching the former wrapper's hard-deadline contract."""
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
    """Compatibility implementation retained for historical direct helper tests."""
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
    """No-op: deadline authority is canonical in ``LiveBlindClearPlanner``."""
    return None
