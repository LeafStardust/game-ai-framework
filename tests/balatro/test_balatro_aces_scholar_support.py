from types import SimpleNamespace

from games.balatro.jokers.dna import DNAJoker
from games.balatro.jokers.scholar import ScholarJoker
from games.balatro.strategy import NEUTRAL, SILVER
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_conditional_relationships import conditional_joker_relationship
from games.balatro.strategy_tree_catalog import TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY
from games.balatro.strategy_tree_tracker import TreeAwareStateAwareBalatroStrategyTracker


def _card(rank, suit):
    return SimpleNamespace(rank=rank, suit=suit, enhancement="", seal="", edition="")


def _deck(extra_aces=0):
    cards = [
        _card(rank, suit)
        for suit in ("Hearts", "Diamonds", "Clubs", "Spades")
        for rank in ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
    ]
    cards.extend(_card("A", "Hearts") for _ in range(extra_aces))
    return cards


def _state(*, jokers=(), extra_aces=0):
    deck = _deck(extra_aces)
    return SimpleNamespace(
        jokers=list(jokers),
        joker_slots=5,
        vouchers=[],
        owned_deck=deck,
        deck=deck,
        hand_levels={},
        hand_play_counts={},
        ante=3,
    )


def _tracker():
    return TreeAwareStateAwareBalatroStrategyTracker(
        RUNTIME_UNIVERSAL_BALATRO_STRATEGIES,
        topology=TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY,
    )


def test_dna_support_requires_scholar_not_ace_concentration():
    dna = DNAJoker()
    assert conditional_joker_relationship(_state(extra_aces=4), "aces", dna) == NEUTRAL
    assert conditional_joker_relationship(_state(jokers=(ScholarJoker(),)), "aces", dna) == SILVER


def test_scholar_dna_strengthens_aces_resolution():
    tracker = _tracker()
    resolution = tracker.observe(_state(jokers=(ScholarJoker(), DNAJoker())))
    assert resolution.dominant_strategy_id == "aces"
    assert resolution.assessment("aces").score >= 11.0
