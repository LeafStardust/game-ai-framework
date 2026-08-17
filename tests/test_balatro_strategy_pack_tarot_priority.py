from games.balatro.actions import SELECT_PACK_CARD, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.jokers.scholar import ScholarJoker
from games.balatro.live.pack import LivePackChoice
from games.balatro.playbook_pack_policy import PlaybookBalatroPackPolicy
from games.balatro.shop_playstyle import BuildAwareShopItemValueEstimator
from games.balatro.state import BalatroState
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_pack_playstyle import StrategyAwarePackPlaystyleEvaluator
from games.balatro.strategy_tree_catalog import TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY
from games.balatro.strategy_tree_tracker import TreeAwareStateAwareBalatroStrategyTracker
from games.balatro.strategy_value import (
    StrategyAwareConsumableSynergyEvaluator,
    StrategyAwareJokerBuildValueEvaluator,
)


def _choice(index, name):
    return LivePackChoice(
        area_index=index,
        address=100 + index,
        data={
            "area_index": index,
            "live_id": 100 + index,
            "label": name,
            "ability_name": name,
            "ability_set": "Tarot",
        },
    )


def _tracker():
    return TreeAwareStateAwareBalatroStrategyTracker(
        RUNTIME_UNIVERSAL_BALATRO_STRATEGIES,
        topology=TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY,
    )


def test_ante_three_aces_prefers_hanged_man_over_unaligned_devil():
    state = BalatroState()
    state.phase = "TAROT_PACK"
    state.ante = 3
    state.money = 10
    state.jokers = [ScholarJoker()]
    state.hand = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Clubs"),
        BalatroCard("A", "Spades"),
        BalatroCard("K", "Diamonds"),
        BalatroCard("7", "Hearts"),
    ]
    state.deck = [
        BalatroCard(rank, suit)
        for rank, suit in (
            ("4", "Spades"),
            ("5", "Clubs"),
            ("6", "Diamonds"),
            ("8", "Hearts"),
            ("9", "Spades"),
            ("10", "Clubs"),
            ("J", "Diamonds"),
            ("Q", "Hearts"),
            ("A", "Clubs"),
        )
    ]
    tracker = _tracker()
    consumable_build = StrategyAwareConsumableSynergyEvaluator(
        strategy_tracker=tracker,
    )
    item_estimator = BuildAwareShopItemValueEstimator(
        joker_build_value=StrategyAwareJokerBuildValueEvaluator(
            strategy_tracker=tracker,
        ),
        consumable_build=consumable_build,
    )
    policy = PlaybookBalatroPackPolicy(
        item_estimator=item_estimator,
        playstyle_evaluator=StrategyAwarePackPlaystyleEvaluator(
            strategy_tracker=tracker,
        ),
    )
    hanged = _choice(0, "The Hanged Man")
    devil = _choice(1, "The Devil")

    ranked = policy.rank_actions(
        state,
        [
            BalatroAction(SELECT_PACK_CARD, target=hanged),
            BalatroAction(SELECT_PACK_CARD, target=devil),
        ],
    )

    assert tracker.observe(state).dominant_strategy_id == "aces"
    assert ranked[0].action.target is hanged
    assert ranked[0].total > ranked[1].total
    assert any(
        "environment-adjusted strategy value=+" in note
        for note in ranked[0].notes
    )
