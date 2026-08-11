import pytest

from games.balatro.live.adaptive_search import adaptive_blind_search_schedule


def test_full_action_budget_escalates_from_four_to_eight_actions():
    schedule = adaptive_blind_search_schedule(
        hands_remaining=4,
        discards_remaining=4,
    )

    assert [config.horizon for config in schedule] == [4, 5, 6, 7, 8]
    assert [config.samples for config in schedule] == [8, 8, 8, 4, 2]
    assert [config.max_nodes for config in schedule] == [2000, 3000, 5000, 5000, 5000]
    assert all(config.child_play_width == 1 for config in schedule)
    assert all(config.child_discard_width == 1 for config in schedule)


def test_schedule_respects_remaining_action_budget():
    schedule = adaptive_blind_search_schedule(
        hands_remaining=2,
        discards_remaining=1,
    )

    assert len(schedule) == 1
    assert schedule[0].horizon == 3
    assert schedule[0].discard_width == 1


def test_schedule_disables_discard_beam_without_discards():
    schedule = adaptive_blind_search_schedule(
        hands_remaining=3,
        discards_remaining=0,
    )

    assert len(schedule) == 1
    assert schedule[0].horizon == 3
    assert schedule[0].discard_width == 0
    assert schedule[0].child_discard_width == 0


def test_schedule_caps_horizon_and_nodes():
    schedule = adaptive_blind_search_schedule(
        hands_remaining=4,
        discards_remaining=4,
        max_horizon=6,
        max_nodes=2500,
    )

    assert [config.horizon for config in schedule] == [4, 5, 6]
    assert [config.max_nodes for config in schedule] == [2000, 2500, 2500]


def test_schedule_rejects_invalid_limits():
    with pytest.raises(ValueError):
        adaptive_blind_search_schedule(
            hands_remaining=4,
            discards_remaining=4,
            max_horizon=0,
        )

    with pytest.raises(ValueError):
        adaptive_blind_search_schedule(
            hands_remaining=4,
            discards_remaining=4,
            max_nodes=0,
        )
