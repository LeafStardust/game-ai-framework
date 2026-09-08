from types import SimpleNamespace

from games.balatro.bonds import (
    BondRank,
    evaluate_clubs_bond,
    evaluate_diamonds_bond,
    evaluate_five_kind_bond,
    evaluate_flush_five_bond,
    evaluate_flush_house_bond,
    evaluate_full_house_bond,
    evaluate_hearts_bond,
    evaluate_low_ranks_bond,
    evaluate_spades_bond,
    evaluate_straight_flush_bond,
)


def _joker(name: str):
    return SimpleNamespace(name=name)


def _card(rank="2", suit="Hearts", enhancement=""):
    return SimpleNamespace(rank=rank, suit=suit, enhancement=enhancement)


def _state(*, jokers=(), deck=(), hand_levels=None):
    return SimpleNamespace(
        jokers=list(jokers),
        owned_deck=list(deck),
        deck=list(deck),
        hand_levels=dict(hand_levels or {}),
    )


def test_full_house_can_emerge_from_permanent_hand_level_without_recipe_joker():
    result = evaluate_full_house_bond(_state(hand_levels={"FULL_HOUSE": 7}))
    assert result.rank == BondRank.R1
    assert result.contribution == 5.0


def test_straight_flush_support_sources_share_one_pool():
    result = evaluate_straight_flush_bond(
        _state(jokers=(_joker("Four Fingers"), _joker("Shortcut")))
    )
    assert result.contribution == 7.0
    assert result.rank == BondRank.R1


def test_five_kind_uses_real_rank_concentration_not_play_count_history():
    deck = tuple(_card("A", "Hearts") for _ in range(7))
    result = evaluate_five_kind_bond(_state(deck=deck))
    assert result.contribution == 4.0
    assert result.rank == BondRank.R1


def test_flush_house_can_emerge_from_hand_level_alone():
    result = evaluate_flush_house_bond(_state(hand_levels={"FLUSH_HOUSE": 7}))
    assert result.rank == BondRank.R1
    assert result.contribution == 5.0


def test_flush_five_same_rank_same_suit_concentration_is_direct_state_evidence():
    deck = tuple(_card("K", "Spades") for _ in range(7))
    result = evaluate_flush_five_bond(_state(deck=deck))
    assert result.rank == BondRank.R1
    assert result.contribution == 5.0


def test_hearts_bloodstone_is_strong_direct_contributor():
    result = evaluate_hearts_bond(_state(jokers=(_joker("Bloodstone"),)))
    assert result.contribution == 7.0
    assert result.rank == BondRank.R1


def test_spades_arrowhead_is_direct_contributor():
    result = evaluate_spades_bond(_state(jokers=(_joker("Arrowhead"),)))
    assert result.contribution == 6.0
    assert result.rank == BondRank.R1


def test_clubs_onyx_agate_is_direct_contributor():
    result = evaluate_clubs_bond(_state(jokers=(_joker("Onyx Agate"),)))
    assert result.contribution == 6.0
    assert result.rank == BondRank.R1


def test_diamonds_rough_gem_is_direct_contributor():
    result = evaluate_diamonds_bond(_state(jokers=(_joker("Rough Gem"),)))
    assert result.contribution == 6.0
    assert result.rank == BondRank.R1


def test_low_ranks_does_not_make_walkie_talkie_a_gold_style_defining_engine():
    walkie = evaluate_low_ranks_bond(_state(jokers=(_joker("Walkie Talkie"),)))
    assert walkie.contribution == 2.0
    assert walkie.rank == BondRank.R0

    hack = evaluate_low_ranks_bond(_state(jokers=(_joker("Hack"),)))
    assert hack.contribution == 6.0
    assert hack.rank == BondRank.R1


def test_walkie_plus_even_is_combined_low_rank_progress_not_a_walkie_bond():
    result = evaluate_low_ranks_bond(
        _state(jokers=(_joker("Walkie Talkie"), _joker("Even Steven")))
    )
    assert result.contribution == 5.0
    assert result.rank == BondRank.R1
