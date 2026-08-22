from types import SimpleNamespace

from games.balatro.bonds import evaluate_hand_repetition_bond
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond


def _joker(name):
    return SimpleNamespace(name=name)


def _state(*, current, previous, counts):
    return SimpleNamespace(
        jokers=[_joker("Card Sharp")],
        current_hand_type=current,
        previous_hand_type=previous,
        hand_play_counts=dict(counts),
    )


def test_card_sharp_realizes_when_current_hand_was_played_earlier_this_round():
    state = _state(current="PAIR", previous="HIGH_CARD", counts={"PAIR": 1, "HIGH_CARD": 1})
    dev = evaluate_hand_repetition_bond(state)
    assert dev.realization == BondRealization.PARTIAL
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.ACTIVE


def test_card_sharp_does_not_require_immediately_previous_hand_match():
    state = _state(current="PAIR", previous="HIGH_CARD", counts={"PAIR": 1})
    out = realize_bond(evaluate_hand_repetition_bond(state), state)
    assert out.realization == BondRealization.ACTIVE


def test_card_sharp_stays_partial_when_current_hand_has_not_been_played_this_round():
    state = _state(current="PAIR", previous="HIGH_CARD", counts={"HIGH_CARD": 2})
    out = realize_bond(evaluate_hand_repetition_bond(state), state)
    assert out.realization == BondRealization.PARTIAL


def test_card_sharp_falls_back_to_previous_hand_when_round_counts_absent():
    state = SimpleNamespace(
        jokers=[_joker("Card Sharp")],
        current_hand_type="PAIR",
        previous_hand_type="PAIR",
    )
    out = realize_bond(evaluate_hand_repetition_bond(state), state)
    assert out.realization == BondRealization.ACTIVE
