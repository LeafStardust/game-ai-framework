from __future__ import annotations

"""Compatibility surface for the former D1 candidate-deadline monkeypatch.

Candidate-generation hard deadline checks and the bounded initial-root bootstrap now
live directly in ``LiveBlindClearPlanner``. This module must not install a second
``_candidate_actions`` authority, but it retains the former helper names and clock
surface so older imports/tests continue to exercise the canonical planner.
"""

from time import perf_counter

import games.balatro.live.blind_clear_planner as _planner_module
from games.balatro.live.blind_clear_planner import (
    LiveBlindClearPlanner,
    PlannerSearchBudgetExceeded,
)


ROOT_BOOTSTRAP_SECONDS = LiveBlindClearPlanner.ROOT_CANDIDATE_BOOTSTRAP_SECONDS


def _compat_perf_counter() -> float:
    """Route the canonical planner clock through this legacy module when imported.

    Historical tests monkeypatch ``d1_candidate_deadline_policy.perf_counter``.
    Keeping this tiny indirection lets those tests control the same clock used by
    the canonical planner without restoring the retired ``_candidate_actions``
    monkeypatch.
    """
    return perf_counter()


# Clock compatibility only: the planner remains the sole candidate/deadline
# implementation authority. Canonical tests may still monkeypatch the planner
# module's ``perf_counter`` directly, which simply replaces this proxy.
_planner_module.perf_counter = _compat_perf_counter


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
