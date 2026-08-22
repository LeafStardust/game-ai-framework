from types import SimpleNamespace

from games.balatro.bonds import (
    BondRank,
    evaluate_blind_skip_bond,
    evaluate_card_destruction_bond,
    evaluate_discard_bond,
    evaluate_enhanced_cards_bond,
    evaluate_hand_repetition_bond,
    evaluate_hand_size_bond,
    evaluate_joker_sacrifice_bond,
    evaluate_sell_value_bond,
)


def _joker(name: str):
    return SimpleNamespace(name=name)


def _card(*, enhancement=""):
    return SimpleNamespace(enhancement=enhancement)


def _state(**kwargs):
    base = dict(
        jokers=[],
        owned_deck=[],
        deck=[],
        discards_per_round=3,
        blinds_skipped=0,
        joker_sell_value_total=0,
        hand_size=8,
        jokers_destroyed=0,
        cards_destroyed=0,
        hand_play_counts={},
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_discard_is_distinct_from_burnt_but_burnt_can_contribute():
    burnt = evaluate_discard_bond(_state(jokers=[_joker("Burnt Joker")]))
    assert burnt.contribution == 3.0
    assert burnt.rank == BondRank.R0
    yorick = evaluate_discard_bond(_state(jokers=[_joker("Yorick")]))
    assert yorick.rank == BondRank.R1


def test_blind_skip_throwback_is_major_and_history_is_additive():
    result = evaluate_blind_skip_bond(
        _state(jokers=[_joker("Throwback")], blinds_skipped=5)
    )
    assert result.contribution == 12.0
    assert result.rank == BondRank.R2


def test_sell_value_can_establish_from_swashbuckler_or_egg():
    assert evaluate_sell_value_bond(_state(jokers=[_joker("Swashbuckler")])).rank == BondRank.R1
    assert evaluate_sell_value_bond(_state(jokers=[_joker("Egg")])).rank == BondRank.R1


def test_hand_size_requires_real_capacity_or_support():
    plain = evaluate_hand_size_bond(_state(hand_size=9))
    assert plain.rank == BondRank.R0
    troubadour = evaluate_hand_size_bond(_state(jokers=[_joker("Troubadour")]))
    assert troubadour.rank == BondRank.R1


def test_joker_sacrifice_scalers_establish_without_history():
    dagger = evaluate_joker_sacrifice_bond(_state(jokers=[_joker("Ceremonial Dagger")]))
    madness = evaluate_joker_sacrifice_bond(_state(jokers=[_joker("Madness")]))
    assert dagger.rank == BondRank.R1
    assert madness.rank == BondRank.R1


def test_card_destruction_and_history_share_one_pool():
    result = evaluate_card_destruction_bond(
        _state(jokers=[_joker("Trading Card")], cards_destroyed=10)
    )
    assert result.contribution == 10.0
    assert result.rank == BondRank.R2


def test_hand_repetition_is_not_created_by_small_play_count_alone():
    weak = evaluate_hand_repetition_bond(_state(hand_play_counts={"PAIR": 5}))
    assert weak.rank == BondRank.R0
    sharp = evaluate_hand_repetition_bond(_state(jokers=[_joker("Card Sharp")]))
    assert sharp.rank == BondRank.R1


def test_enhanced_cards_driver_license_is_major_but_density_alone_is_limited():
    driver = evaluate_enhanced_cards_bond(_state(jokers=[_joker("Driver's License")]))
    assert driver.rank == BondRank.R1
    dense = evaluate_enhanced_cards_bond(
        _state(owned_deck=[_card(enhancement="Mult") for _ in range(24)])
    )
    assert dense.contribution == 7.0
    assert dense.rank == BondRank.R1
