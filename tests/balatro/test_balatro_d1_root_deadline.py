from __future__ import annotations

import pytest

from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.live.blind_clear_planner import PlannerSearchBudgetExceeded
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner


def test_d1_root_structural_priority_checks_wall_clock_before_hand_evaluation():
    planner = D1LiveBlindClearPlanner()

    def expired() -> None:
        raise PlannerSearchBudgetExceeded("expired before root structural ranking")

    planner._check_wall_clock_budget = expired

    with pytest.raises(PlannerSearchBudgetExceeded, match="expired before root structural ranking"):
        planner._direct_child_play_priority(BalatroAction(PLAY_CARDS, cards=[]))
