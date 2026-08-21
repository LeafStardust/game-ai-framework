from types import SimpleNamespace

from games.balatro.bonds import (
    BondRank,
    evaluate_deck_growth_bond,
    evaluate_deck_thinning_bond,
    evaluate_flush_bond,
    evaluate_four_kind_bond,
    evaluate_gold_economy_bond,
    evaluate_played_retrigger_bond,
    evaluate_stone_bond,
    evaluate_straight_bond,
    evaluate_three_kind_bond,
    evaluate_two_pair_bond,
)


def _joker(name):
    return SimpleNamespace(name=name)


def _card(rank="2", suit="Hearts", enhancement="", seal=""):
    return SimpleNamespace(rank=rank, suit=suit, enhancement=enhancement, seal=seal, is_stone=(enhancement == "Stone"))


def _state(*, jokers=(), deck=(), hand_levels=None):
    return SimpleNamespace(
        jokers=list(jokers),
        owned_deck=list(deck),
        deck=list(deck),
        hand_levels=dict(hand_levels or {}),
    )


def test_two_pair_can_emerge_from_spare_trousers_or_levels():
    assert evaluate_two_pair_bond(_state(jokers=(_joker("Spare Trousers"),))).rank == BondRank.R1
    assert evaluate_two_pair_bond(_state(hand_levels={"TWO_PAIR": 7})).rank == BondRank.R1


def test_three_kind_has_direct_joker_path():
    result = evaluate_three_kind_bond(_state(jokers=(_joker("The Trio"),)))
    assert result.rank == BondRank.R1
    assert result.contribution == 6.0


def test_four_kind_includes_flower_pot_as_minor_contributor_not_own_bond():
    result = evaluate_four_kind_bond(_state(jokers=(_joker("The Family"), _joker("Flower Pot"))))
    assert result.contribution == 9.0
    assert result.rank == BondRank.R2


def test_straight_combines_shortcut_and_hand_levels():
    result = evaluate_straight_bond(_state(jokers=(_joker("Shortcut"),), hand_levels={"STRAIGHT": 4}))
    assert result.contribution == 8.0
    assert result.rank == BondRank.R2


def test_flush_can_emerge_from_real_suit_density():
    deck = tuple(_card(suit="Hearts") for _ in range(20))
    result = evaluate_flush_bond(_state(deck=deck))
    assert result.contribution == 3.0
    assert result.rank == BondRank.R0
    stronger = evaluate_flush_bond(_state(jokers=(_joker("Droll Joker"),), deck=deck))
    assert stronger.rank == BondRank.R1


def test_played_retrigger_is_independent_from_held_retrigger():
    result = evaluate_played_retrigger_bond(_state(jokers=(_joker("Sock and Buskin"),)))
    assert result.contribution == 6.0
    assert result.rank == BondRank.R1


def test_stone_uses_jokers_and_persistent_density():
    deck = tuple(_card(enhancement="Stone") for _ in range(6))
    result = evaluate_stone_bond(_state(jokers=(_joker("Marble Joker"),), deck=deck))
    assert result.contribution == 11.0
    assert result.rank == BondRank.R2


def test_gold_economy_owns_gold_card_density_not_held_cards():
    deck = tuple(_card(enhancement="Gold") for _ in range(6))
    result = evaluate_gold_economy_bond(_state(deck=deck))
    assert result.contribution == 6.0
    assert result.rank == BondRank.R1


def test_deck_thinning_counts_actual_persistent_reduction():
    deck = tuple(_card() for _ in range(40))
    result = evaluate_deck_thinning_bond(_state(deck=deck))
    assert result.contribution == 5.0
    assert result.rank == BondRank.R1


def test_deck_growth_counts_quality_sources_and_persistent_growth():
    deck = tuple(_card() for _ in range(60))
    result = evaluate_deck_growth_bond(_state(jokers=(_joker("DNA"),), deck=deck))
    assert result.contribution == 9.0
    assert result.rank == BondRank.R2
