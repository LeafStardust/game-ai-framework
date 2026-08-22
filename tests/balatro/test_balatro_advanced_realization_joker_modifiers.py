from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _joker(name):
    return SimpleNamespace(name=name)


def _card(rank, suit):
    return SimpleNamespace(rank=rank, suit=suit, enhancement="")


def _dev(bond_id):
    return BondDevelopment(
        bond_id=bond_id,
        unlocked=True,
        contribution=10.0,
        rank=BondRank.R2,
        next_rank_threshold=15.0,
        contributions=(),
        realization=BondRealization.PARTIAL,
    )


def test_advanced_realizer_normalizes_space_separated_runtime_hand_names():
    state = SimpleNamespace(current_hand_type="Full House", hand=[], jokers=[])
    assert realize_bond(_dev("full_house"), state).realization == BondRealization.ACTIVE


def test_four_fingers_can_realize_four_card_straight_flush():
    state = SimpleNamespace(
        current_hand_type="",
        jokers=[_joker("Four Fingers")],
        hand=[
            _card("5", "Hearts"),
            _card("6", "Hearts"),
            _card("7", "Hearts"),
            _card("8", "Hearts"),
        ],
    )
    assert realize_bond(_dev("straight_flush"), state).realization == BondRealization.ACTIVE


def test_shortcut_can_realize_gapped_straight_flush():
    state = SimpleNamespace(
        current_hand_type="",
        jokers=[_joker("Shortcut")],
        hand=[
            _card("2", "Spades"),
            _card("4", "Spades"),
            _card("6", "Spades"),
            _card("8", "Spades"),
            _card("10", "Spades"),
        ],
    )
    assert realize_bond(_dev("straight_flush"), state).realization == BondRealization.ACTIVE


def test_four_fingers_can_realize_flush_house_with_offsuit_full_house_card():
    state = SimpleNamespace(
        current_hand_type="",
        jokers=[_joker("Four Fingers")],
        hand=[
            _card("8", "Spades"),
            _card("8", "Spades"),
            _card("8", "Hearts"),
            _card("6", "Spades"),
            _card("6", "Spades"),
        ],
    )
    assert realize_bond(_dev("flush_house"), state).realization == BondRealization.ACTIVE


def test_four_fingers_can_realize_flush_five_with_fifth_card_offsuit():
    state = SimpleNamespace(
        current_hand_type="",
        jokers=[_joker("Four Fingers")],
        hand=[
            _card("7", "Clubs"),
            _card("7", "Clubs"),
            _card("7", "Clubs"),
            _card("7", "Clubs"),
            _card("7", "Hearts"),
        ],
    )
    assert realize_bond(_dev("flush_five"), state).realization == BondRealization.ACTIVE


def test_smeared_joker_can_realize_mixed_red_flush_house():
    state = SimpleNamespace(
        current_hand_type="",
        jokers=[_joker("Smeared Joker")],
        hand=[
            _card("K", "Hearts"),
            _card("K", "Diamonds"),
            _card("K", "Hearts"),
            _card("9", "Diamonds"),
            _card("9", "Hearts"),
        ],
    )
    assert realize_bond(_dev("flush_house"), state).realization == BondRealization.ACTIVE


def test_smeared_joker_can_realize_mixed_black_flush_five():
    state = SimpleNamespace(
        current_hand_type="",
        jokers=[_joker("Smeared Joker")],
        hand=[
            _card("7", "Spades"),
            _card("7", "Clubs"),
            _card("7", "Spades"),
            _card("7", "Clubs"),
            _card("7", "Spades"),
        ],
    )
    assert realize_bond(_dev("flush_five"), state).realization == BondRealization.ACTIVE
