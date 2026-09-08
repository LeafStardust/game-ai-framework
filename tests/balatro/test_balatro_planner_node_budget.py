import pytest

from games.balatro.live.blind_clear_planner import (
    LiveBlindClearPlanner,
    PlannerSearchBudgetExceeded,
)


def test_planner_node_budget_never_counts_past_cap():
    planner = LiveBlindClearPlanner(max_nodes=2)

    planner._consume_node()
    planner._consume_node()

    assert planner.nodes_evaluated == 2

    with pytest.raises(PlannerSearchBudgetExceeded):
        planner._consume_node()

    assert planner.nodes_evaluated == 2
