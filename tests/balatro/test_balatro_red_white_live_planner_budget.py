from games.balatro.playbook import (
    RED_WHITE_LIVE_MAX_SEARCH_NODES,
    default_balatro_playbooks,
)


def test_red_white_live_planner_uses_bounded_node_budget():
    playbook = default_balatro_playbooks().get("RED", "WHITE")
    planner = playbook.strategy["planner"]

    assert RED_WHITE_LIVE_MAX_SEARCH_NODES == 2500
    assert planner["max_search_nodes"] == 2500
    assert planner["max_horizon"] == 5
    assert planner["max_search_seconds"] == 8.0
    assert planner["search_schedule_mode"] == "probe-deepest"
