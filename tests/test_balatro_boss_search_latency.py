from types import SimpleNamespace

from games.balatro.live.runtime.playstyle_autonomous_runner import (
    BOSS_D1_MAX_HORIZON,
    BOSS_D1_MAX_SEARCH_NODES,
    LATE_ANTE_D1_MAX_HORIZON,
    LATE_ANTE_D1_MAX_SEARCH_NODES,
    LATE_ANTE_D1_START,
    _bounded_d1_limits,
)


def test_club_boss_search_is_capped_to_interactive_budget():
    state = SimpleNamespace(boss_name="The Club")

    horizon, nodes, reason = _bounded_d1_limits(state, 5, 5000)

    assert reason == "boss"
    assert horizon == BOSS_D1_MAX_HORIZON == 2
    assert nodes == BOSS_D1_MAX_SEARCH_NODES == 500


def test_ante_eight_small_blind_search_is_capped_to_interactive_budget():
    state = SimpleNamespace(boss_name=None, ante=8)

    horizon, nodes, reason = _bounded_d1_limits(state, 5, 5000)

    assert reason == "late_ante"
    assert LATE_ANTE_D1_START == 7
    assert horizon == LATE_ANTE_D1_MAX_HORIZON == 2
    assert nodes == LATE_ANTE_D1_MAX_SEARCH_NODES == 750


def test_early_non_boss_search_keeps_playbook_budget():
    state = SimpleNamespace(boss_name=None, ante=6)

    assert _bounded_d1_limits(state, 5, 5000) == (5, 5000, None)
