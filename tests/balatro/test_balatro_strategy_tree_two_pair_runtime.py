from types import SimpleNamespace

import pytest

from games.balatro.strategy import BANNED, BRONZE, GOLD, NEUTRAL, SILVER
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_conditional_relationships import (
    conditional_joker_relationship,
)
from games.balatro.strategy_tree_catalog import (
    TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY,
)
from games.balatro.strategy_tree_tracker import (
    TreeAwareStateAwareBalatroStrategyTracker,
)


class MadJoker:
    pass


class CleverJoker:
    pass


class SpareTrousersJoker:
    pass


class TheDuoJoker:
    pass


class CardSharpJoker:
    pass


class ObeliskJoker:
    pass


def _named(name: str):
    return SimpleNamespace(name=name)


def _state(*, jokers=(), hand_levels=None, hand_play_counts=None, ante=1):
    return SimpleNamespace(
        jokers=list(jokers),
        vouchers=[],
        owned_deck=[],
        deck=[],
        hand_levels=dict(hand_levels or {}),
        hand_play_counts=dict(hand_play_counts or {}),
        ante=ante,
    )


def _tracker():
    return TreeAwareStateAwareBalatroStrategyTracker(
        RUNTIME_UNIVERSAL_BALATRO_STRATEGIES,
        topology=TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY,
    )


def _by_id(resolution):
    return {assessment.strategy_id: assessment for assessment in resolution.assessments}


def test_two_pair_is_a_standalone_leaf_without_fake_specializations():
    topology = TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY

    assert topology.is_leaf("two_pair") is True
    assert "two_pair_core" not in topology.nodes
    assert "two_pair_trousers_square" not in topology.nodes


def test_two_pair_ranks_its_own_direct_evidence():
    tracker = _tracker()
    state = _state(jokers=(MadJoker(),))

    resolution = tracker.observe(state)
    by_id = _by_id(resolution)
    nodes = tracker.tree_node_scores()

    assert by_id["two_pair"].score == pytest.approx(3.0)
    assert nodes["two_pair"].direct_evidence == pytest.approx(3.0)
    assert nodes["two_pair"].active is True


def test_two_pair_level_investment_builds_standalone_leaf_evidence():
    tracker = _tracker()
    state = _state(hand_levels={"TWO_PAIR": 2})

    resolution = tracker.observe(state)
    by_id = _by_id(resolution)
    nodes = tracker.tree_node_scores()

    assert nodes["two_pair"].direct_evidence == pytest.approx(0.5)
    assert by_id["two_pair"].score == pytest.approx(0.5)


def test_two_pair_play_count_alone_never_creates_strategy_evidence():
    tracker = _tracker()
    state = _state(hand_play_counts={"TWO_PAIR": 999, "PAIR": 0})

    resolution = tracker.observe(state)
    by_id = _by_id(resolution)

    assert by_id["two_pair"].score == pytest.approx(0.0)


def test_two_pair_parent_does_not_ban_competing_poker_hand_support():
    definition = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["two_pair"]

    for competing in (
        "Half Joker",
        "The Trio",
        "The Family",
        "Runner",
        "The Order",
        "The Tribe",
    ):
        assert definition.relationship_for(_named(competing), kind="JOKER") == NEUTRAL

    assert definition.relationship_for(MadJoker(), kind="JOKER") == SILVER
    assert definition.relationship_for(CleverJoker(), kind="JOKER") == SILVER
    assert definition.relationship_for(SpareTrousersJoker(), kind="JOKER") == GOLD
    assert definition.relationship_for(TheDuoJoker(), kind="JOKER") == SILVER
    assert definition.relationship_for(_named("Jolly Joker"), kind="JOKER") == BRONZE
    assert definition.relationship_for(_named("Uranus"), kind="PLANET") == GOLD


def test_direct_pair_structure_and_conditional_repeat_support_are_separate():
    ordinary = _state()

    assert conditional_joker_relationship(ordinary, "two_pair", TheDuoJoker()) == NEUTRAL
    assert conditional_joker_relationship(ordinary, "two_pair", CardSharpJoker()) == NEUTRAL

    invested = _state(hand_levels={"TWO_PAIR": 2})
    assert conditional_joker_relationship(invested, "two_pair", TheDuoJoker()) == SILVER
    assert conditional_joker_relationship(invested, "two_pair", CardSharpJoker()) == SILVER


def test_spare_trousers_ranks_standalone_two_pair_leaf():
    tracker = _tracker()
    state = _state(jokers=(SpareTrousersJoker(),))

    resolution = tracker.observe(state)
    by_id = _by_id(resolution)

    assert by_id["two_pair"].score == pytest.approx(8.0)
    assert resolution.dominant_strategy_id == "two_pair"


def test_two_pair_obelisk_conflict_uses_history_only_for_obelisk_mechanic():
    history_only = _state(hand_play_counts={"TWO_PAIR": 8, "HIGH_CARD": 2})
    assert conditional_joker_relationship(history_only, "two_pair", ObeliskJoker()) == NEUTRAL

    committed = _state(
        hand_levels={"TWO_PAIR": 2},
        hand_play_counts={"TWO_PAIR": 8, "HIGH_CARD": 2},
    )
    assert conditional_joker_relationship(committed, "two_pair", ObeliskJoker()) == BANNED

    pivoted = _state(
        hand_levels={"TWO_PAIR": 2},
        hand_play_counts={"TWO_PAIR": 8, "HIGH_CARD": 9},
    )
    assert conditional_joker_relationship(pivoted, "two_pair", ObeliskJoker()) == NEUTRAL
