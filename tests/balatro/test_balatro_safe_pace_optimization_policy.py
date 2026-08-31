from types import SimpleNamespace

from games.balatro.live.path_aware_hand_action_engine import (
    PathAwareLiveHandActionDecisionEngine,
)
from games.balatro.safe_pace_optimization_policy import _safe_search_schedule


def test_live_safe_search_is_one_shallow_advisory_pass():
    schedule = _safe_search_schedule(
        hands_remaining=4,
        discards_remaining=4,
        max_horizon=8,
        max_nodes=5000,
    )
    assert len(schedule) == 1
    assert schedule[0].horizon == 2
    assert schedule[0].max_nodes == 750
    assert schedule[0].discard_width == 2


def test_safe_search_never_expands_to_engineered_five_action_clear():
    schedule = _safe_search_schedule(
        hands_remaining=4,
        discards_remaining=4,
        max_horizon=5,
        max_nodes=20000,
    )
    assert [item.horizon for item in schedule] == [2]
    assert schedule[0].max_nodes == 750


def test_production_d1_engine_applies_safe_pace_schedule():
    state = SimpleNamespace(hands_remaining=4, discards_remaining=4)
    engine = PathAwareLiveHandActionDecisionEngine(
        max_horizon=8,
        max_search_nodes=5000,
    )

    schedule = engine._search_schedule(state)
    expected = _safe_search_schedule(
        hands_remaining=4,
        discards_remaining=4,
        max_horizon=8,
        max_nodes=5000,
    )

    assert schedule == expected
    assert len(schedule) == 1
    assert schedule[0].horizon == 2
    assert schedule[0].max_nodes == 750
