from types import SimpleNamespace

from games.balatro.bonds import BondRank, evaluate_hearts_bond
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond


def _card(suit="Clubs", enhancement=""):
    return SimpleNamespace(rank="7", suit=suit, enhancement=enhancement)


def _joker(name):
    return SimpleNamespace(name=name)


def test_wild_cards_contribute_to_every_suit_density():
    deck = [_card("Clubs", "Wild") for _ in range(17)]
    state = SimpleNamespace(jokers=[], owned_deck=deck, deck=deck)
    dev = evaluate_hearts_bond(state)
    assert dev.contribution == 3.0
    assert dev.rank == BondRank.R0


def test_wild_card_realizes_hearts_payoff_despite_printed_club_suit():
    wild = _card("Clubs", "Wild")
    deck = [wild] + [_card("Hearts") for _ in range(16)]
    state = SimpleNamespace(
        jokers=[_joker("Lusty Joker")],
        scoring_cards=[wild], played_cards=[wild], current_played_cards=[wild],
        owned_deck=deck, deck=deck,
    )
    dev = evaluate_hearts_bond(state)
    assert dev.rank >= BondRank.R1
    out = realize_bond(dev, state)
    assert out.realization == BondRealization.ACTIVE
