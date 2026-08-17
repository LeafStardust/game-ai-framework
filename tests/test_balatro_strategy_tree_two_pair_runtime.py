from types import SimpleNamespace

import pytest

from games.balatro.strategy import BANNED, GOLD, NEUTRAL, SILVER
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


def test_two_pair_topology_has_internal_parent_core_fallback_and_specialized_child():
    topology = TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY

    assert topology.is_leaf("two_pair") is False
    assert topology.is_leaf("two_pair_core") is True
    assert topology.is_leaf("two_pair_trousers_square") is True
    assert topology.nodes["two_pair_core"].is_fallback_leaf is True
    assert topology.parent_by_id["two_pair_core"] == "two_pair"
    assert topology.parent_by_id["two_pair_trousers_square"] == "two_pair"


def test_core_two_pair_inherits_only_broad_parent_evidence():
    tracker = _tracker()
    state = _state(jokers=(MadJoker(),))

    resolution = tracker.observe(state)
    by_id = _by_id(resolution)
    nodes = tracker.tree_node_scores()

    assert "two_pair" not in by_id
    assert nodes["two_pair"].direct_evidence == pytest.approx(3.0)
    assert nodes["two_pair_core"].direct_evidence == pytest.approx(0.0)
    assert by_id["two_pair_core"].score == pytest.approx(3.0)
    assert by_id["two_pair_trousers_square"].score == pytest.approx(0.0)
    assert resolution.dominant_strategy_id == "two_pair_core"


def test_two_pair_level_investment_builds_parent_not_core_direct_evidence():
    tracker = _tracker()
    state = _state(hand_levels={"TWO_PAIR": 2})

    resolution = tracker.observe(state)
    by_id = _by_id(resolution)
    nodes = tracker.tree_node_scores()

    assert nodes["two_pair"].direct_evidence == pytest.approx(0.5)
    assert nodes["two_pair_core"].direct_evidence == pytest.approx(0.0)
    assert by_id["two_pair_core"].score == pytest.approx(0.5)


def test_two_pair_play_count_alone_never_creates_strategy_evidence():
    tracker = _tracker()
    state = _state(hand_play_counts={"TWO_PAIR": 999, "PAIR": 0})

    resolution = tracker.observe(state)
    by_id = _by_id(resolution)

    assert by_id["two_pair_core"].score == pytest.approx(0.0)
    assert by_id["two_pair_trousers_square"].score == pytest.approx(0.0)


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
    assert definition.relationship_for(_named("Uranus"), kind="PLANET") == GOLD


def test_generic_pair_and_repeat_support_cannot_start_two_pair_from_zero():
    ordinary = _state()

    assert conditional_joker_relationship(ordinary, "two_pair", TheDuoJoker()) == NEUTRAL
    assert conditional_joker_relationship(ordinary, "two_pair", CardSharpJoker()) == NEUTRAL

    invested = _state(hand_levels={"TWO_PAIR": 2})
    assert conditional_joker_relationship(invested, "two_pair", TheDuoJoker()) == SILVER
    assert conditional_joker_relationship(invested, "two_pair", CardSharpJoker()) == SILVER


def test_spare_trousers_routes_to_specialized_child_and_suppresses_core():
    tracker = _tracker()
    state = _state(jokers=(SpareTrousersJoker(),))

    resolution = tracker.observe(state)
    by_id = _by_id(resolution)

    assert by_id["two_pair_trousers_square"].score == pytest.approx(5.0)
    assert by_id["two_pair_core"].score == pytest.approx(0.0)
    assert resolution.dominant_strategy_id == "two_pair_trousers_square"


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
