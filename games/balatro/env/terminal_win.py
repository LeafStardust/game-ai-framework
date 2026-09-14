"""Exact headless terminal boundary for clearing the Ante-8 Boss."""

from __future__ import annotations

from games.balatro.blinds.blind import BlindType
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError


def require_ante_8_win_boundary(run: HeadlessRunState) -> None:
    """Validate the pinned-source win notification boundary without advancing Ante."""
    if not isinstance(run, HeadlessRunState):
        raise TypeError("run must be HeadlessRunState")

    state = run.public
    progression = run.require_blind_progression_state()
    selection = run.require_boss_selection_state()
    if (
        state.phase != "ROUND_EVAL"
        or state.blind is None
        or getattr(state.blind, "type", None) is not BlindType.BOSS
        or state.ante != selection.win_ante
        or progression.blind_on_deck != "Boss"
        or progression.boss_status != "Current"
        or progression.boss_name != state.boss_name
    ):
        raise HeadlessTransitionError(
            "Ante-8 win requires the exact current showdown boundary"
        )
    requirement = getattr(state.blind, "requirement", None)
    if (
        isinstance(requirement, bool)
        or not isinstance(requirement, int)
        or requirement < 0
        or isinstance(state.score, bool)
        or not isinstance(state.score, int)
        or state.score < requirement
    ):
        raise HeadlessTransitionError(
            "Ante-8 win requires the showdown target to be met"
        )
