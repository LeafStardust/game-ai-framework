import pytest

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.adaptive_search import (
    AdaptiveRecommendationSummary,
    adaptive_blind_search_schedule,
    stable_discard_consensus,
)


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


def test_extended_node_budget_adds_deepest_horizon_intensification():
    schedule = adaptive_blind_search_schedule(
        hands_remaining=4,
        discards_remaining=3,
        max_horizon=8,
        max_nodes=10000,
    )

    assert [config.horizon for config in schedule] == [4, 5, 6, 7, 7, 7]
    assert [config.max_nodes for config in schedule] == [
        2000,
        3000,
        5000,
        5000,
        10000,
        10000,
    ]

    wider_root = schedule[-2]
    assert wider_root.samples == 8
    assert wider_root.play_width == 3
    assert wider_root.discard_width == 2
    assert wider_root.child_play_width == 1

    wider_child = schedule[-1]
    assert wider_child.samples == 4
    assert wider_child.play_width == 3
    assert wider_child.discard_width == 2
    assert wider_child.child_play_width == 2


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


def _recommendation(action, indices, probability, expected_score):
    return AdaptiveRecommendationSummary(
        action=action,
        indices=indices,
        clear_probability=probability,
        expected_score=expected_score,
    )


def test_consensus_discard_accepts_three_deepening_agreements():
    recommendations = (
        _recommendation(PLAY_CARDS, (1, 2, 3), 0.0, 4198.0),
        _recommendation(DISCARD_CARDS, (6,), 0.0, 5158.698),
        _recommendation(DISCARD_CARDS, (6,), 0.046512, 6189.442),
        _recommendation(DISCARD_CARDS, (6,), 0.209302, 6904.884),
    )

    assert stable_discard_consensus(recommendations)


def test_consensus_discard_ignores_strictly_dominated_noisy_tail():
    recommendations = (
        _recommendation(DISCARD_CARDS, (0, 1), 0.125, 6465.5),
        _recommendation(DISCARD_CARDS, (0, 1), 0.125, 6824.0),
        _recommendation(DISCARD_CARDS, (0, 1), 0.125, 6824.0),
        _recommendation(DISCARD_CARDS, (4, 5), 0.029412, 6704.324),
    )

    assert stable_discard_consensus(recommendations)


def test_consensus_discard_rejects_changed_indexes():
    recommendations = (
        _recommendation(DISCARD_CARDS, (6,), 0.0, 5158.0),
        _recommendation(DISCARD_CARDS, (5,), 0.1, 6200.0),
        _recommendation(DISCARD_CARDS, (6,), 0.2, 6900.0),
    )

    assert not stable_discard_consensus(recommendations)


def test_consensus_discard_rejects_regressing_projection():
    recommendations = (
        _recommendation(DISCARD_CARDS, (6,), 0.0, 5158.0),
        _recommendation(DISCARD_CARDS, (6,), 0.2, 6900.0),
        _recommendation(DISCARD_CARDS, (6,), 0.1, 6800.0),
    )

    assert not stable_discard_consensus(recommendations)


def test_consensus_discard_rejects_one_objective_tradeoff_tail():
    recommendations = (
        _recommendation(DISCARD_CARDS, (0, 1), 0.125, 6465.5),
        _recommendation(DISCARD_CARDS, (0, 1), 0.125, 6824.0),
        _recommendation(DISCARD_CARDS, (0, 1), 0.125, 6824.0),
        _recommendation(DISCARD_CARDS, (4, 5), 0.20, 6704.324),
    )

    assert not stable_discard_consensus(recommendations)


def test_consensus_discard_rejects_scored_play():
    recommendations = (
        _recommendation(PLAY_CARDS, (1, 2), 0.2, 5000.0),
        _recommendation(PLAY_CARDS, (1, 2), 0.3, 6000.0),
        _recommendation(PLAY_CARDS, (1, 2), 0.4, 7000.0),
    )

    assert not stable_discard_consensus(recommendations)
