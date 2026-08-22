from types import SimpleNamespace

from games.balatro.bonds import (
    BondRank,
    evaluate_blind_skip_bond,
    evaluate_card_destruction_bond,
    evaluate_discard_bond,
    evaluate_enhanced_cards_bond,
    evaluate_hand_repetition_bond,
    evaluate_joker_sacrifice_bond,
    evaluate_sell_value_bond,
)


def _joker(name: str):
    return SimpleNamespace(name=name)


def _card(*, enhancement=""):
    return SimpleNamespace(enhancement=enhancement)


def _state(**kwargs):
    base = dict(
        jokers=[], owned_deck=[], deck=[], discards_per_round=3,
        blinds_skipped=0, joker_sell_value_total=0,
        jokers_destroyed=0, cards_destroyed=0, hand_play_counts={},
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_discard_requires_non_burnt_discard_payoff():
    burnt = evaluate_discard_bond(_state(jokers=[_joker("Burnt Joker")], discards_per_round=6))
    assert burnt.rank == BondRank.LOCKED
    yorick = evaluate_discard_bond(_state(jokers=[_joker("Yorick")]))
    assert yorick.rank == BondRank.R1


def test_burnt_can_deepen_discard_after_discard_bond_exists():
    result = evaluate_discard_bond(_state(jokers=[_joker("Castle"), _joker("Burnt Joker")]))
    assert result.contribution == 8.0
    assert result.rank == BondRank.R1


def test_blind_skip_requires_throwback_and_history_is_additive():
    history_only = evaluate_blind_skip_bond(_state(blinds_skipped=8))
    cola_only = evaluate_blind_skip_bond(_state(jokers=[_joker("Diet Cola")]))
    assert history_only.rank == BondRank.LOCKED
    assert cola_only.rank == BondRank.LOCKED
    result = evaluate_blind_skip_bond(_state(jokers=[_joker("Throwback")], blinds_skipped=5))
    assert result.contribution == 12.0
    assert result.rank == BondRank.R2


def test_sell_value_requires_swashbuckler():
    assert evaluate_sell_value_bond(_state(jokers=[_joker("Egg")])).rank == BondRank.LOCKED
    result = evaluate_sell_value_bond(_state(jokers=[_joker("Swashbuckler"), _joker("Egg")]))
    assert result.contribution == 12.0
    assert result.rank == BondRank.R2


def test_joker_sacrifice_requires_current_scaler():
    history = evaluate_joker_sacrifice_bond(_state(jokers_destroyed=10))
    riff = evaluate_joker_sacrifice_bond(_state(jokers=[_joker("Riff-Raff")]))
    assert history.rank == BondRank.LOCKED
    assert riff.rank == BondRank.LOCKED
    dagger = evaluate_joker_sacrifice_bond(_state(jokers=[_joker("Ceremonial Dagger")]))
    madness = evaluate_joker_sacrifice_bond(_state(jokers=[_joker("Madness")]))
    assert dagger.rank == BondRank.R1
    assert madness.rank == BondRank.R1


def test_card_destruction_requires_current_engine():
    history = evaluate_card_destruction_bond(_state(cards_destroyed=16))
    assert history.rank == BondRank.LOCKED
    result = evaluate_card_destruction_bond(_state(jokers=[_joker("Trading Card")], cards_destroyed=10))
    assert result.contribution == 10.0
    assert result.rank == BondRank.R2


def test_hand_repetition_requires_current_payoff():
    history = evaluate_hand_repetition_bond(_state(hand_play_counts={"PAIR": 30}))
    assert history.rank == BondRank.LOCKED
    sharp = evaluate_hand_repetition_bond(_state(jokers=[_joker("Card Sharp")], hand_play_counts={"PAIR": 10}))
    assert sharp.contribution == 10.0
    assert sharp.rank == BondRank.R2


def test_enhanced_cards_is_drivers_license_defining_bond():
    dense = evaluate_enhanced_cards_bond(_state(owned_deck=[_card(enhancement="Mult") for _ in range(24)]))
    assert dense.rank == BondRank.LOCKED
    driver = evaluate_enhanced_cards_bond(
        _state(jokers=[_joker("Driver's License")], owned_deck=[_card(enhancement="Mult") for _ in range(16)])
    )
    assert driver.contribution == 12.0
    assert driver.rank == BondRank.R2
