import pytest

from games.balatro.strategy_topology import StrategyNodeSpec, StrategyTopology
from games.balatro.strategy_tree_scoring import StrategyTreeEvidenceScorer


def _split_topology():
    return StrategyTopology(
        (
            StrategyNodeSpec("root", "Root"),
            StrategyNodeSpec("specific_a", "Specific A", parent_strategy_id="root"),
            StrategyNodeSpec("specific_b", "Specific B", parent_strategy_id="root"),
        )
    )


def test_descendant_evidence_propagates_upward_with_decay():
    scorer = StrategyTreeEvidenceScorer(_split_topology(), upward_decay=0.5)

    scores = scorer.score({"specific_a": 4.0})

    assert scores["specific_a"].direct_evidence == 4.0
    assert scores["specific_a"].foundation_score == 4.0
    assert scores["root"].direct_evidence == 0.0
    assert scores["root"].foundation_score == 2.0


def test_ancestor_evidence_does_not_auto_activate_specific_children():
    scorer = StrategyTreeEvidenceScorer(_split_topology())

    scores = scorer.score({"root": 5.0})

    assert scores["root"].on_frontier is True
    assert scores["root"].active is True
    assert scores["root"].effective_score == 5.0
    assert scores["specific_a"].on_frontier is False
    assert scores["specific_a"].active is False
    assert scores["specific_a"].effective_score == 0.0
    assert scores["specific_b"].active is False
    assert scores["specific_b"].effective_score == 0.0


def test_specific_child_inherits_only_native_ancestor_evidence_without_double_counting():
    scorer = StrategyTreeEvidenceScorer(_split_topology(), upward_decay=0.5)

    scores = scorer.score({"root": 2.0, "specific_a": 4.0})

    assert scores["root"].foundation_score == 4.0
    assert scores["specific_a"].effective_score == 6.0


def test_specific_child_evidence_replaces_generic_parent_on_frontier():
    scorer = StrategyTreeEvidenceScorer(_split_topology())

    scores = scorer.score({"root": 3.0, "specific_a": 2.0})

    assert scores["specific_a"].active is True
    assert scores["specific_a"].effective_score == 5.0
    assert scores["root"].on_frontier is False
    assert scores["root"].active is False
    assert scores["root"].effective_score == 0.0


def test_subthreshold_child_structure_keeps_generic_parent_actionable():
    scorer = StrategyTreeEvidenceScorer(
        _split_topology(),
        specific_activation_floor=1.0,
    )

    scores = scorer.score({"root": 3.0, "specific_a": 0.35})

    assert scores["specific_a"].active is False
    assert scores["specific_a"].effective_score == 0.0
    assert scores["root"].on_frontier is True
    assert scores["root"].active is True
    assert scores["root"].effective_score == 3.0


def test_weak_positive_evidence_remains_active_for_unsplit_root_leaf():
    topology = StrategyTopology((StrategyNodeSpec("pair", "Pair"),))
    scorer = StrategyTreeEvidenceScorer(topology, specific_activation_floor=1.0)

    scores = scorer.score({"pair": 0.5})

    assert scores["pair"].active is True
    assert scores["pair"].effective_score == 0.5


def test_descendant_evidence_advances_to_deepest_established_frontier():
    topology = StrategyTopology(
        (
            StrategyNodeSpec("root", "Root"),
            StrategyNodeSpec("branch", "Branch", parent_strategy_id="root"),
            StrategyNodeSpec("root_peer", "Root Peer", parent_strategy_id="root"),
            StrategyNodeSpec("deep_leaf", "Deep Leaf", parent_strategy_id="branch"),
            StrategyNodeSpec("deep_peer", "Deep Peer", parent_strategy_id="branch"),
        )
    )
    scorer = StrategyTreeEvidenceScorer(topology)

    scores = scorer.score({"root": 3.0, "deep_leaf": 2.0})

    assert scores["deep_leaf"].active is True
    assert scores["branch"].on_frontier is False
    assert scores["root"].on_frontier is False


def test_actionable_ranking_uses_current_frontier_only():
    scorer = StrategyTreeEvidenceScorer(_split_topology())

    ranked = scorer.rank_actionable(
        {
            "root": 2.0,
            "specific_a": 1.0,
            "specific_b": 3.0,
        }
    )

    assert tuple(score.strategy_id for score in ranked) == (
        "specific_b",
        "specific_a",
    )
    assert all(score.on_frontier for score in ranked)


def test_negative_child_conflict_does_not_propagate_as_negative_parent_foundation():
    scorer = StrategyTreeEvidenceScorer(_split_topology())

    scores = scorer.score({"specific_a": -8.0})

    assert scores["specific_a"].direct_evidence == -8.0
    assert scores["specific_a"].active is False
    assert scores["root"].foundation_score == 0.0


def test_deep_descendant_decay_uses_distance():
    topology = StrategyTopology(
        (
            StrategyNodeSpec("root", "Root"),
            StrategyNodeSpec("branch", "Branch", parent_strategy_id="root"),
            StrategyNodeSpec("root_peer", "Root Peer", parent_strategy_id="root"),
            StrategyNodeSpec("leaf", "Leaf", parent_strategy_id="branch"),
            StrategyNodeSpec("leaf_peer", "Leaf Peer", parent_strategy_id="branch"),
        )
    )
    scorer = StrategyTreeEvidenceScorer(topology, upward_decay=0.5)

    scores = scorer.score({"leaf": 4.0})

    assert scores["branch"].foundation_score == 2.0
    assert scores["root"].foundation_score == 1.0
    assert scores["leaf"].effective_score == 4.0


def test_unknown_direct_evidence_node_is_rejected():
    scorer = StrategyTreeEvidenceScorer(_split_topology())

    with pytest.raises(KeyError, match="unknown strategy nodes"):
        scorer.score({"not_in_tree": 1.0})
