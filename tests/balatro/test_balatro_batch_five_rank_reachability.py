from types import SimpleNamespace

from games.balatro.bonds.catalogue_batch_five import (
    evaluate_blind_skip_bond,
    evaluate_card_destruction_bond,
    evaluate_enhanced_cards_bond,
    evaluate_hand_repetition_bond,
    evaluate_joker_sacrifice_bond,
    evaluate_sell_value_bond,
)
from games.balatro.bonds.model import BondRank


def _state(**values):
    defaults = {
        "jokers": [],
        "deck": [],
        "owned_deck": [],
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


def test_blind_skip_capstone_is_reachable_from_literal_contributor_ceiling():
    development = evaluate_blind_skip_bond(
        _state(jokers=["Throwback", "Diet Cola"], blinds_skipped=8)
    )

    assert development.contribution == 18.0
    assert development.rank == BondRank.R5
    assert development.next_rank_threshold is None


def test_sell_value_capstone_is_reachable_from_literal_contributor_ceiling():
    development = evaluate_sell_value_bond(
        _state(
            jokers=["Swashbuckler", "Gift Card", "Egg"],
            joker_sell_value_total=60,
        )
    )

    assert development.contribution == 25.0
    assert development.rank == BondRank.R5
    assert development.next_rank_threshold is None


def test_joker_sacrifice_capstone_is_reachable_from_literal_contributor_ceiling():
    development = evaluate_joker_sacrifice_bond(
        _state(
            jokers=["Ceremonial Dagger", "Madness", "Riff-Raff"],
            jokers_destroyed=10,
        )
    )

    assert development.contribution == 23.0
    assert development.rank == BondRank.R5
    assert development.next_rank_threshold is None


def test_card_destruction_capstone_is_reachable_from_literal_contributor_ceiling():
    development = evaluate_card_destruction_bond(
        _state(
            jokers=["Canio", "Trading Card", "Sixth Sense", "Glass Joker"],
            cards_destroyed=16,
        )
    )

    assert development.contribution == 26.0
    assert development.rank == BondRank.R5
    assert development.next_rank_threshold is None


def test_hand_repetition_capstone_is_reachable_from_literal_contributor_ceiling():
    development = evaluate_hand_repetition_bond(
        _state(
            jokers=["Card Sharp", "Supernova"],
            hand_play_counts={"HIGH_CARD": 30},
        )
    )

    assert development.contribution == 20.0
    assert development.rank == BondRank.R5
    assert development.next_rank_threshold is None


def test_enhanced_cards_capstone_is_reachable_from_literal_contributor_ceiling():
    enhanced_deck = [SimpleNamespace(enhancement="Gold") for _ in range(24)]
    development = evaluate_enhanced_cards_bond(
        _state(
            jokers=["Driver's License", "Midas Mask", "Marble Joker"],
            owned_deck=enhanced_deck,
        )
    )

    assert development.contribution == 20.0
    assert development.rank == BondRank.R5
    assert development.next_rank_threshold is None
