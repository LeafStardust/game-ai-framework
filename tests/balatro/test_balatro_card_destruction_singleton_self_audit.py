from types import SimpleNamespace

from games.balatro.bonds.model import BondDevelopment, BondRank, BondRealization
from games.balatro.bonds.realization import realize_bond


def _dev():
    return BondDevelopment(
        bond_id="card_destruction",
        unlocked=True,
        contribution=22.0,
        rank=BondRank.R4,
        next_rank_threshold=30.0,
        contributions=(),
        realization=BondRealization.PARTIAL,
    )


def _card(rank="2"):
    return SimpleNamespace(rank=rank, enhancement="")


def test_trading_card_requires_single_card_first_discard():
    a, b = _card("2"), _card("3")
    state = SimpleNamespace(
        jokers=[SimpleNamespace(name="Trading Card")],
        hand=[a, b],
        selected_cards=[a, b],
        first_discard_available=True,
    )
    assert realize_bond(_dev(), state).realization == BondRealization.PARTIAL


def test_trading_card_realizes_on_single_card_first_discard():
    a = _card("2")
    state = SimpleNamespace(
        jokers=[SimpleNamespace(name="Trading Card")],
        hand=[a],
        selected_cards=[a],
        first_discard_available=True,
    )
    assert realize_bond(_dev(), state).realization == BondRealization.ACTIVE


def test_sixth_sense_requires_single_six_first_hand():
    six, seven = _card("6"), _card("7")
    state = SimpleNamespace(
        jokers=[SimpleNamespace(name="Sixth Sense")],
        hand=[six, seven],
        cards_to_play=[six, seven],
        first_hand_available=True,
    )
    assert realize_bond(_dev(), state).realization == BondRealization.PARTIAL


def test_sixth_sense_realizes_on_single_six_first_hand():
    six = _card("6")
    state = SimpleNamespace(
        jokers=[SimpleNamespace(name="Sixth Sense")],
        hand=[six],
        cards_to_play=[six],
        first_hand_available=True,
    )
    assert realize_bond(_dev(), state).realization == BondRealization.ACTIVE
