from types import SimpleNamespace

from games.balatro.strategy import (
    BANNED,
    BRONZE,
    ENHANCEMENT_EVIDENCE_WEIGHT,
    GOLD,
    HAND_LEVEL_EVIDENCE_WEIGHT,
    NEUTRAL,
    SPECTRAL_USE_EVIDENCE_WEIGHT,
    TAROT_USE_EVIDENCE_WEIGHT,
)
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_conditional_relationships import (
    conditional_joker_relationship,
)
from games.balatro.strategy_tree_catalog import (
    SECTION_ONE_NODE_IDS,
    SECTION_ONE_ROOT_IDS,
    TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY,
)


def _joker(name: str):
    return SimpleNamespace(name=name)


class ObeliskJoker:
    pass


def _state(*, jokers=(), hand_levels=None, hand_play_counts=None):
    return SimpleNamespace(
        jokers=list(jokers),
        hand_levels=dict(hand_levels or {}),
        hand_play_counts=dict(hand_play_counts or {}),
        owned_deck=[],
        deck=[],
    )


def test_section_one_contains_twelve_roots_and_thirteen_terminal_strategies():
    topology = TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY

    assert len(SECTION_ONE_ROOT_IDS) == 12
    assert len(SECTION_ONE_NODE_IDS) == 14
    terminal_ids = {
        strategy_id
        for strategy_id in SECTION_ONE_NODE_IDS
        if topology.is_leaf(strategy_id)
    }
    assert len(terminal_ids) == 13
    assert terminal_ids == SECTION_ONE_NODE_IDS - {"high_card"}


def test_section_one_has_no_one_child_or_fake_core_nodes():
    topology = TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY

    assert not any("core" in strategy_id for strategy_id in SECTION_ONE_NODE_IDS)
    assert all(
        len(topology.children_by_id[strategy_id]) != 1
        for strategy_id in SECTION_ONE_NODE_IDS
    )


def test_straight_is_standalone_and_superposition_is_support_evidence():
    topology = TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY
    straight = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["straight"]

    assert topology.is_leaf("straight") is True
    assert straight.relationship_for(_joker("Superposition"), kind="JOKER") == BRONZE
    assert straight.relationship_for(_joker("The Order"), kind="JOKER") == GOLD
    assert straight.directed_tarots == frozenset({"strength", "death"})


def test_non_joker_evidence_weights_are_independent_contract_values():
    flush_five = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["flush_five"]

    assert HAND_LEVEL_EVIDENCE_WEIGHT == 0.50
    assert TAROT_USE_EVIDENCE_WEIGHT == 0.30
    assert SPECTRAL_USE_EVIDENCE_WEIGHT == 0.50
    assert ENHANCEMENT_EVIDENCE_WEIGHT == 0.35
    assert flush_five.directed_tarots == frozenset(
        {"death", "strength", "thelovers"}
    )
    assert flush_five.directed_spectrals == frozenset(
        {"cryptid", "ouija", "sigil"}
    )


def test_high_card_parent_and_children_do_not_duplicate_joker_evidence():
    definitions = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
    parent = definitions["high_card"]

    parent_jokers = (
        parent.gold_jokers
        | parent.silver_jokers
        | parent.bronze_jokers
        | parent.banned_jokers
    )
    for child_id in ("high_card_stuntman", "high_card_baron_mime"):
        child = definitions[child_id]
        child_jokers = (
            child.gold_jokers
            | child.silver_jokers
            | child.bronze_jokers
            | child.banned_jokers
        )
        assert parent_jokers.isdisjoint(child_jokers)


def test_obelisk_conflict_requires_real_straight_commitment_and_history():
    obelisk = ObeliskJoker()
    uncommitted = _state(hand_play_counts={"STRAIGHT": 9, "PAIR": 1})
    committed = _state(
        hand_levels={"STRAIGHT": 2},
        hand_play_counts={"STRAIGHT": 9, "PAIR": 1},
    )

    assert conditional_joker_relationship(uncommitted, "straight", obelisk) == NEUTRAL
    assert conditional_joker_relationship(committed, "straight", obelisk) == BANNED
