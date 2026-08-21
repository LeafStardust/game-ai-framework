from types import SimpleNamespace

from games.balatro.bonds import (
    BOND_RELATIONSHIPS,
    BondRank,
    evaluate_aces_bond,
    evaluate_cash_bond,
    evaluate_face_cards_bond,
    evaluate_glass_bond,
    evaluate_held_cards_bond,
    evaluate_held_retrigger_bond,
    evaluate_high_card_bond,
    evaluate_lucky_bond,
    evaluate_no_discard_bond,
    evaluate_pair_bond,
    evaluate_steel_bond,
)


def _joker(name):
    return SimpleNamespace(name=name)


def _card(rank="2", enhancement="", seal=""):
    return SimpleNamespace(rank=rank, enhancement=enhancement, seal=seal)


def _state(*, jokers=(), deck=(), hand_levels=None, hand_size=8, money=0, glass_cards_destroyed=0):
    return SimpleNamespace(
        jokers=list(jokers),
        owned_deck=list(deck),
        deck=list(deck),
        hand_levels=dict(hand_levels or {}),
        hand_size=hand_size,
        money=money,
        glass_cards_destroyed=glass_cards_destroyed,
    )


def test_mime_is_exclusive_to_held_retrigger_not_held_cards():
    state = _state(jokers=(_joker("Mime"),))
    assert evaluate_held_cards_bond(state).contribution == 0.0
    assert evaluate_held_cards_bond(state).rank == BondRank.R0
    assert evaluate_held_retrigger_bond(state).contribution == 6.0
    assert evaluate_held_retrigger_bond(state).rank == BondRank.R1


def test_red_seals_can_develop_held_retrigger_without_mime():
    state = _state(deck=tuple(_card(seal="Red") for _ in range(4)))
    result = evaluate_held_retrigger_bond(state)
    assert result.contribution == 5.0
    assert result.rank == BondRank.R1


def test_steel_is_its_own_bond_and_can_overlap_held_cards():
    state = _state(deck=tuple(_card(enhancement="Steel") for _ in range(4)))
    assert evaluate_steel_bond(state).contribution == 6.0
    assert evaluate_steel_bond(state).rank == BondRank.R1
    assert evaluate_held_cards_bond(state).contribution == 5.0
    assert evaluate_held_cards_bond(state).rank == BondRank.R1


def test_pair_uses_pair_specific_jokers_and_permanent_level():
    state = _state(jokers=(_joker("The Duo"),), hand_levels={"PAIR": 4})
    result = evaluate_pair_bond(state)
    assert result.contribution == 9.0
    assert result.rank == BondRank.R2


def test_pair_play_history_is_not_required_for_pair_development():
    state = _state(jokers=(_joker("Jolly Joker"),))
    result = evaluate_pair_bond(state)
    assert result.contribution == 4.0
    assert result.rank == BondRank.R1


def test_high_card_and_pair_can_share_half_joker_without_becoming_same_bond():
    state = _state(jokers=(_joker("Half Joker"),))
    assert evaluate_high_card_bond(state).contribution == 3.0
    assert evaluate_pair_bond(state).contribution == 2.0
    assert evaluate_high_card_bond(state).rank == BondRank.R0
    assert evaluate_pair_bond(state).rank == BondRank.R0


def test_stuntman_establishes_high_card():
    result = evaluate_high_card_bond(_state(jokers=(_joker("Stuntman"),)))
    assert result.contribution == 6.0
    assert result.rank == BondRank.R1


def test_aces_requires_real_ace_support_not_generic_hand_strength():
    state = _state(
        jokers=(_joker("Scholar"),),
        deck=tuple(_card(rank="A") for _ in range(8)),
    )
    result = evaluate_aces_bond(state)
    assert result.contribution == 11.0
    assert result.rank == BondRank.R2


def test_dna_only_adds_ace_bridge_when_ace_density_is_meaningful():
    low = evaluate_aces_bond(_state(jokers=(_joker("DNA"),), deck=tuple(_card(rank="A") for _ in range(4))))
    high = evaluate_aces_bond(_state(jokers=(_joker("DNA"),), deck=tuple(_card(rank="A") for _ in range(6))))
    assert low.contribution == 1.0
    assert high.contribution == 7.0


def test_green_and_burglar_stack_inside_no_discard_bond():
    result = evaluate_no_discard_bond(_state(jokers=(_joker("Green Joker"), _joker("Burglar"))))
    assert result.contribution == 12.0
    assert result.rank == BondRank.R2


def test_cash_rank_uses_engine_plus_bankroll_not_cash_alone():
    cash_only = evaluate_cash_bond(_state(money=100))
    engine = evaluate_cash_bond(_state(jokers=(_joker("Bull"), _joker("Bootstraps")), money=100))
    assert cash_only.contribution == 5.0
    assert cash_only.rank == BondRank.R1
    assert engine.contribution == 15.0
    assert engine.rank == BondRank.R3


def test_lucky_cat_and_lucky_density_share_one_pool():
    state = _state(jokers=(_joker("Lucky Cat"),), deck=tuple(_card(enhancement="Lucky") for _ in range(6)))
    result = evaluate_lucky_bond(state)
    assert result.contribution == 11.0
    assert result.rank == BondRank.R2


def test_glass_joker_accumulated_destruction_is_persistent_development():
    state = _state(
        jokers=(_joker("Glass Joker"),),
        deck=tuple(_card(enhancement="Glass") for _ in range(3)),
        glass_cards_destroyed=3,
    )
    result = evaluate_glass_bond(state)
    assert result.contribution == 11.0
    assert result.rank == BondRank.R2


def test_face_cards_can_emerge_from_jokers_and_density():
    deck = tuple(_card(rank=rank) for rank in ("J", "Q", "K") for _ in range(6))
    result = evaluate_face_cards_bond(_state(jokers=(_joker("Sock and Buskin"),), deck=deck))
    assert result.contribution == 8.0
    assert result.rank == BondRank.R1


def test_sparse_relationships_only_encode_meaningful_edges():
    assert BOND_RELATIONSHIPS[frozenset(("burnt", "no_discard"))] == "CONFLICT"
    assert BOND_RELATIONSHIPS[frozenset(("held_cards", "held_retrigger"))] == "SYNERGY"
    assert BOND_RELATIONSHIPS[frozenset(("held_cards", "steel"))] == "SYNERGY"
    assert frozenset(("pair", "lucky")) not in BOND_RELATIONSHIPS
