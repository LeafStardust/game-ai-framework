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


class TheDuoJoker:
    pass


class JollyJoker:
    pass


class SlyJoker:
    pass


class HalfJoker:
    pass


class SupernovaJoker:
    pass


class CardSharpJoker:
    pass


class SpaceJoker:
    pass


class BurntJoker:
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


def _pair_assessment(tracker, state):
    return next(
        assessment
        for assessment in tracker.assess(state)
        if assessment.strategy_id == "pair"
    )


def test_pair_tree_owned_static_relationships_are_pair_specific():
    definition = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["pair"]

    assert definition.relationship_for(TheDuoJoker(), kind="JOKER") == GOLD
    assert definition.relationship_for(JollyJoker(), kind="JOKER") == SILVER
    assert definition.relationship_for(SlyJoker(), kind="JOKER") == SILVER

    assert definition.relationship_for(HalfJoker(), kind="JOKER") == SILVER
    # Repeat-hand support is conditional so it cannot create Pair from zero by
    # ownership alone.
    assert definition.relationship_for(CardSharpJoker(), kind="JOKER") == NEUTRAL

    # Supporting a different poker hand is not a mechanical contradiction.
    for competing in (
        "The Trio",
        "Spare Trousers",
        "Runner",
        "The Order",
        "The Tribe",
    ):
        assert definition.relationship_for(_named(competing), kind="JOKER") == NEUTRAL

    assert definition.relationship_for(_named("Mercury"), kind="PLANET") == GOLD
    assert definition.relationship_for(_named("Death"), kind="CONSUMABLE") == NEUTRAL


def test_pair_play_count_alone_never_creates_strategy_evidence():
    tracker = _tracker()
    state = _state(hand_play_counts={"PAIR": 999, "HIGH_CARD": 0})

    pair = _pair_assessment(tracker, state)

    assert pair.score == pytest.approx(0.0)
    assert tracker.observe(state).dominant_strategy_id is None


def test_pair_direct_joker_establishes_standalone_leaf():
    tracker = _tracker()
    state = _state(jokers=(TheDuoJoker(),))

    pair = _pair_assessment(tracker, state)
    node = tracker.tree_node_scores()["pair"]

    assert pair.gold_owned == 1
    assert pair.score == pytest.approx(5.0)
    assert node.is_leaf is True
    assert node.active is True
    assert node.direct_evidence == pytest.approx(5.0)
    # Global dominance is intentionally not asserted during hybrid migration:
    # The Duo still appears in some not-yet-migrated legacy hand definitions.


def test_generic_small_hand_and_repeat_support_requires_independent_pair_commitment():
    ordinary = _state()
    for joker in (
        HalfJoker(),
        SupernovaJoker(),
        CardSharpJoker(),
        SpaceJoker(),
        BurntJoker(),
    ):
        assert conditional_joker_relationship(ordinary, "pair", joker) == NEUTRAL

    invested = _state(hand_levels={"PAIR": 2})
    for joker in (
        HalfJoker(),
        SupernovaJoker(),
        CardSharpJoker(),
        SpaceJoker(),
        BurntJoker(),
    ):
        assert conditional_joker_relationship(invested, "pair", joker) == SILVER

    direct = _state(jokers=(JollyJoker(),))
    assert conditional_joker_relationship(direct, "pair", HalfJoker()) == SILVER


def test_half_joker_is_direct_pair_evidence_while_repeat_support_is_conditional():
    tracker = _tracker()

    unsupported = _state(jokers=(HalfJoker(),))
    assert _pair_assessment(tracker, unsupported).score == pytest.approx(3.0)

    invested = _state(
        jokers=(HalfJoker(),),
        hand_levels={"PAIR": 2},
    )
    pair = _pair_assessment(tracker, invested)
    assert pair.silver_owned == 1
    # +3 Silver relationship plus +0.5 from one permanent Pair level above base.
    assert pair.score == pytest.approx(3.5)


def test_pair_obelisk_conflict_needs_non_history_commitment_and_most_played_pair():
    history_only = _state(hand_play_counts={"PAIR": 8, "HIGH_CARD": 2})
    assert (
        conditional_joker_relationship(history_only, "pair", ObeliskJoker())
        == NEUTRAL
    )

    committed = _state(
        hand_levels={"PAIR": 2},
        hand_play_counts={"PAIR": 8, "HIGH_CARD": 2},
    )
    assert (
        conditional_joker_relationship(committed, "pair", ObeliskJoker())
        == BANNED
    )

    pivoted_history = _state(
        hand_levels={"PAIR": 2},
        hand_play_counts={"PAIR": 8, "HIGH_CARD": 9},
    )
    assert (
        conditional_joker_relationship(pivoted_history, "pair", ObeliskJoker())
        == NEUTRAL
    )


def test_pair_candidate_index_uses_conditional_support_and_obelisk_conflict():
    state = _state(
        hand_levels={"PAIR": 2},
        hand_play_counts={"PAIR": 8, "HIGH_CARD": 2},
    )
    tracker = _tracker()
    tracker.assess(state)

    half_relationships = tracker._relationships_for(HalfJoker(), kind="JOKER")
    obelisk_relationships = tracker._relationships_for(ObeliskJoker(), kind="JOKER")

    assert half_relationships["pair"] == SILVER
    assert obelisk_relationships["pair"] == BANNED
