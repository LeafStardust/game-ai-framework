from types import SimpleNamespace

from games.balatro.jokers.pareidolia import PareidoliaJoker
from games.balatro.jokers.smiley_face import SmileyFaceJoker
from games.balatro.strategy import SILVER
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_conditional_relationships import conditional_joker_relationship
from games.balatro.strategy_tree_catalog import TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY
from games.balatro.strategy_tree_tracker import TreeAwareStateAwareBalatroStrategyTracker
from games.balatro.strategy_value import StrategyAwareJokerBuildValueEvaluator


def _state(*, jokers):
    return SimpleNamespace(
        jokers=list(jokers),
        vouchers=[],
        owned_deck=[],
        deck=[],
        hand_levels={},
        hand_play_counts={},
        ante=3,
        joker_slots=5,
    )


def _tracker():
    return TreeAwareStateAwareBalatroStrategyTracker(
        RUNTIME_UNIVERSAL_BALATRO_STRATEGIES,
        topology=TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY,
    )


def test_smiley_face_is_silver_support_once_pareidolia_is_owned():
    state = _state(jokers=(PareidoliaJoker(), SmileyFaceJoker()))
    assert conditional_joker_relationship(
        state,
        "face_pareidolia",
        SmileyFaceJoker(),
    ) == SILVER


def test_pareidolia_primary_route_retains_smiley_as_real_engine_support():
    state = _state(jokers=(PareidoliaJoker(), SmileyFaceJoker()))
    tracker = _tracker()
    evaluator = StrategyAwareJokerBuildValueEvaluator(strategy_tracker=tracker)
    value = evaluator.evaluate(state, SmileyFaceJoker())

    # Contract: Pareidolia + Smiley must keep Smiley at a real aligned retention
    # value. The exact rationale text is diagnostic and may legitimately differ
    # when another aligned-value path already reaches the same floor.
    assert conditional_joker_relationship(
        state,
        "face_pareidolia",
        SmileyFaceJoker(),
    ) == SILVER
    assert value.total_gain >= 6.0
    assert value.strategic_adjustment > 0.0
