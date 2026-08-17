from types import SimpleNamespace

import pytest

from games.balatro.strategy import GOLD, NEUTRAL
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_conditional_relationships import (
    StateAwareBalatroStrategyTracker,
)
from games.balatro.strategy_tree_catalog import (
    TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY,
)
from games.balatro.strategy_tree_tracker import (
    TreeAwareStateAwareBalatroStrategyTracker,
)


def _joker(name: str):
    return SimpleNamespace(name=name)


def _card(
    rank="2",
    suit="Hearts",
    *,
    enhancement="",
    seal="",
    edition="",
):
    return SimpleNamespace(
        rank=rank,
        suit=suit,
        enhancement=enhancement,
        seal=seal,
        edition=edition,
    )


def _state(*, jokers=(), deck=(), hand_levels=None, ante=1):
    return SimpleNamespace(
        jokers=list(jokers),
        vouchers=[],
        owned_deck=list(deck),
        deck=list(deck),
        hand_levels=dict(hand_levels or {}),
        hand_play_counts={},
        ante=ante,
    )


def _tracker():
    return TreeAwareStateAwareBalatroStrategyTracker(
        RUNTIME_UNIVERSAL_BALATRO_STRATEGIES,
        topology=TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY,
    )


def _assessment_by_id(resolution):
    return {assessment.strategy_id: assessment for assessment in resolution.assessments}


def test_burnt_joker_builds_high_card_parent_and_ranks_only_core_leaf():
    tracker = _tracker()
    state = _state(jokers=(_joker("Burnt Joker"),))

    resolution = tracker.observe(state)
    by_id = _assessment_by_id(resolution)
    nodes = tracker.tree_node_scores()

    assert "high_card" not in by_id
    assert by_id["high_card_core"].score == pytest.approx(5.0)
    assert by_id["high_card_stuntman"].score == pytest.approx(0.0)
    assert by_id["high_card_baron_mime"].score == pytest.approx(0.0)
    assert nodes["high_card"].direct_evidence == pytest.approx(5.0)
    assert nodes["high_card_core"].active is True
    assert nodes["high_card_stuntman"].active is False
    assert nodes["high_card_baron_mime"].active is False
    assert resolution.dominant_strategy_id == "high_card_core"


def test_stuntman_specific_evidence_suppresses_core_and_inherits_parent_foundation():
    tracker = _tracker()
    state = _state(
        jokers=(
            _joker("Burnt Joker"),
            _joker("Stuntman"),
        )
    )

    resolution = tracker.observe(state)
    by_id = _assessment_by_id(resolution)
    nodes = tracker.tree_node_scores()

    assert by_id["high_card_stuntman"].score == pytest.approx(10.0)
    assert by_id["high_card_core"].score == pytest.approx(0.0)
    assert nodes["high_card"].foundation_score == pytest.approx(7.5)
    assert nodes["high_card_stuntman"].direct_evidence == pytest.approx(5.0)
    assert resolution.dominant_strategy_id == "high_card_stuntman"


def test_baron_mime_leaf_can_establish_deep_high_card_route_early():
    tracker = _tracker()
    state = _state(
        jokers=(
            _joker("Burnt Joker"),
            _joker("Baron"),
            _joker("Mime"),
        )
    )

    resolution = tracker.observe(state)
    by_id = _assessment_by_id(resolution)

    assert by_id["high_card_baron_mime"].score == pytest.approx(11.0)
    assert by_id["high_card_core"].score == pytest.approx(0.0)
    assert resolution.dominant_strategy_id == "high_card_baron_mime"


def test_subthreshold_held_structure_does_not_choose_baron_mime_branch():
    tracker = _tracker()
    state = _state(
        jokers=(_joker("Burnt Joker"),),
        deck=(_card("K", "Spades", enhancement="Steel"),),
    )

    resolution = tracker.observe(state)
    by_id = _assessment_by_id(resolution)

    assert by_id["high_card_core"].score == pytest.approx(5.0)
    assert by_id["high_card_baron_mime"].score == pytest.approx(0.0)
    assert resolution.dominant_strategy_id == "high_card_core"


def test_high_card_leaf_inherits_parent_hand_prescription_without_duplicate_hand_evidence():
    tracker = _tracker()
    state = _state(
        jokers=(_joker("Stuntman"),),
        hand_levels={"HIGH_CARD": 3},
    )

    resolution = tracker.observe(state)
    by_id = _assessment_by_id(resolution)

    assert tracker.primary_hands_for("high_card_stuntman") == ("HIGH_CARD",)
    # Root receives +1.0 from two permanent hand levels; the child receives only
    # its own Stuntman evidence and then inherits the root once.
    assert by_id["high_card_stuntman"].score == pytest.approx(6.0)


def test_parent_candidate_relationship_maps_to_current_specific_leaf():
    tracker = _tracker()
    state = _state(jokers=(_joker("Stuntman"),), ante=4)

    evaluation = tracker.evaluate_item(
        state,
        _joker("Burnt Joker"),
        kind="JOKER",
    )

    assert evaluation.strategy_id == "high_card_stuntman"
    assert evaluation.tier == GOLD
    assert evaluation.active_alignment is True
    assert evaluation.projected_score == pytest.approx(10.0)
    assert evaluation.value > 0.0


def test_specific_candidate_projects_parent_inheritance_without_self_funding_bonus():
    tracker = _tracker()
    state = _state(jokers=(_joker("Burnt Joker"),), ante=4)

    evaluation = tracker.evaluate_item(
        state,
        _joker("Stuntman"),
        kind="JOKER",
    )

    assert evaluation.strategy_id == "high_card_stuntman"
    assert evaluation.tier == GOLD
    assert evaluation.projected_score == pytest.approx(10.0)
    assert evaluation.pivot_candidate is True
    # The candidate can reveal a pivot but cannot create its own current-strategy
    # purchase bonus before it is actually owned.
    assert evaluation.value == pytest.approx(0.0)


def test_old_competing_hand_jokers_are_not_high_card_banned_relationships():
    definition = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["high_card"]

    assert definition.relationship_for(_joker("Jolly Joker"), kind="JOKER") == NEUTRAL
    assert definition.relationship_for(_joker("The Trio"), kind="JOKER") == NEUTRAL


def test_unsplit_strategy_scores_remain_identical_during_hybrid_migration():
    state = _state(
        jokers=(
            _joker("The Duo"),
            _joker("The Trio"),
        )
    )
    legacy = StateAwareBalatroStrategyTracker(RUNTIME_UNIVERSAL_BALATRO_STRATEGIES)
    tree = _tracker()

    legacy_pair = next(
        assessment
        for assessment in legacy.assess(state)
        if assessment.strategy_id == "pair"
    )
    tree_pair = next(
        assessment
        for assessment in tree.assess(state)
        if assessment.strategy_id == "pair"
    )

    assert tree_pair.score == pytest.approx(legacy_pair.score)
