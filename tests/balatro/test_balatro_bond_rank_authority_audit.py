from types import SimpleNamespace

from games.balatro.bonds import (
    BondRank,
    evaluate_blind_skip_bond,
    evaluate_deck_thinning_bond,
    evaluate_glass_bond,
    evaluate_held_cards_bond,
    evaluate_high_card_bond,
    evaluate_jacks_bond,
    evaluate_lucky_bond,
    evaluate_tarot_bond,
)


def _joker(name: str):
    return SimpleNamespace(name=name)


def _voucher(name: str):
    return SimpleNamespace(name=name)


def _card(*, rank="2", suit="Hearts", enhancement="", seal=""):
    return SimpleNamespace(rank=rank, suit=suit, enhancement=enhancement, seal=seal, is_stone=(enhancement == "Stone"))


def _state(**kwargs):
    base = dict(
        jokers=[],
        vouchers=[],
        owned_deck=[],
        deck=[],
        hand_levels={},
        hand_size=8,
        blinds_skipped=0,
        cards_destroyed=0,
        jokers_destroyed=0,
        hand_play_counts={},
        joker_sell_value_total=0,
        discards_per_round=3,
        money=0,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_extreme_permanent_hand_investment_can_reach_high_card_capstone_with_real_payoff():
    result = evaluate_high_card_bond(
        _state(jokers=[_joker("Stuntman"), _joker("Half Joker")], hand_levels={"HIGH_CARD": 25})
    )
    assert result.contribution == 27.0
    assert result.rank == BondRank.R5


def test_ordinary_hand_levels_do_not_receive_capstone_authority():
    result = evaluate_high_card_bond(_state(hand_levels={"HIGH_CARD": 7}))
    assert result.contribution == 5.0
    assert result.rank == BondRank.R1


def test_complete_held_cards_structure_can_reach_r5_without_fake_mime_quota():
    deck = [_card(enhancement="Steel") for _ in range(6)]
    result = evaluate_held_cards_bond(
        _state(
            jokers=[_joker("Baron"), _joker("Shoot the Moon"), _joker("Raised Fist")],
            owned_deck=deck,
            hand_size=11,
        )
    )
    assert result.contribution == 22.0
    assert result.rank == BondRank.R5


def test_lucky_capstone_requires_full_lucky_package_not_one_piece():
    weak = evaluate_lucky_bond(_state(jokers=[_joker("Lucky Cat")]))
    assert weak.rank == BondRank.R1
    deck = [_card(enhancement="Lucky") for _ in range(10)]
    capstone = evaluate_lucky_bond(
        _state(jokers=[_joker("Lucky Cat"), _joker("Oops! All 6s")], owned_deck=deck)
    )
    assert capstone.contribution == 17.0
    assert capstone.rank == BondRank.R5


def test_glass_full_structure_can_reach_capstone():
    deck = [_card(enhancement="Glass") for _ in range(10)]
    result = evaluate_glass_bond(
        _state(jokers=[_joker("Glass Joker")], owned_deck=deck, glass_cards_destroyed=10)
    )
    assert result.contribution == 19.0
    assert result.rank == BondRank.R5


def test_extreme_deck_thinning_is_established_even_without_current_thinning_joker():
    deck = [_card() for _ in range(34)]
    result = evaluate_deck_thinning_bond(_state(owned_deck=deck))
    assert result.contribution == 7.0
    assert result.rank == BondRank.R2


def test_throwback_plus_deep_skip_history_can_reach_skip_capstone():
    result = evaluate_blind_skip_bond(
        _state(jokers=[_joker("Throwback"), _joker("Diet Cola")], blinds_skipped=8)
    )
    assert result.contribution == 18.0
    assert result.rank == BondRank.R5


def test_all_major_tarot_infrastructure_can_reach_r5_but_single_access_piece_stays_r1():
    single = evaluate_tarot_bond(_state(jokers=[_joker("Cartomancer")]))
    assert single.rank == BondRank.R1
    full = evaluate_tarot_bond(
        _state(
            jokers=[_joker("Cartomancer"), _joker("Vagabond"), _joker("Hallucination"), _joker("Fortune Teller")],
            vouchers=[_voucher("Tarot Merchant"), _voucher("Tarot Tycoon")],
        )
    )
    assert full.contribution == 29.0
    assert full.rank == BondRank.R5


def test_extreme_jack_density_can_eventually_reach_capstone_with_hit_the_road():
    deck = [_card(rank="J") for _ in range(44)]
    result = evaluate_jacks_bond(_state(jokers=[_joker("Hit the Road")], owned_deck=deck))
    assert result.contribution == 30.0
    assert result.rank == BondRank.R5
