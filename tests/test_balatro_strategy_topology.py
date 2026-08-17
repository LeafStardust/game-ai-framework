import pytest

from games.balatro.strategy_topology import (
    HIGH_CARD_STRATEGY_TOPOLOGY,
    StrategyNodeSpec,
    StrategyTopology,
)


def test_flat_nodes_are_both_roots_and_rankable_leaves():
    topology = StrategyTopology(
        (
            StrategyNodeSpec("pair", "Pair"),
            StrategyNodeSpec("flush", "Flush"),
        )
    )

    assert topology.roots == ("flush", "pair")
    assert topology.leaves == ("flush", "pair")
    assert topology.is_leaf("pair") is True
    assert topology.ancestors("pair") == ()
    assert topology.path("pair") == ("pair",)


def test_high_card_subtree_exposes_only_specific_children_as_leaves():
    topology = HIGH_CARD_STRATEGY_TOPOLOGY

    assert topology.roots == ("high_card",)
    assert topology.is_leaf("high_card") is False
    assert topology.leaves == (
        "high_card_baron_mime",
        "high_card_core",
        "high_card_stuntman",
    )
    assert topology.ancestors("high_card_baron_mime") == ("high_card",)
    assert topology.path("high_card_baron_mime") == (
        "high_card",
        "high_card_baron_mime",
    )
    assert topology.nodes["high_card_core"].is_fallback_leaf is True


def test_topology_rejects_missing_parent():
    with pytest.raises(ValueError, match="missing parent"):
        StrategyTopology(
            (
                StrategyNodeSpec(
                    "baron_mime",
                    "Baron-Mime",
                    parent_strategy_id="high_card",
                ),
            )
        )


def test_topology_rejects_cycles():
    with pytest.raises(ValueError, match="cycle"):
        StrategyTopology(
            (
                StrategyNodeSpec("a", "A", parent_strategy_id="b"),
                StrategyNodeSpec("b", "B", parent_strategy_id="a"),
            )
        )


def test_topology_rejects_duplicate_node_ids():
    with pytest.raises(ValueError, match="duplicate"):
        StrategyTopology(
            (
                StrategyNodeSpec("same", "First"),
                StrategyNodeSpec("same", "Second"),
            )
        )
