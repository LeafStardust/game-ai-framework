from types import SimpleNamespace

from games.balatro.bonds import BondRank, evaluate_no_face_cards_bond


def _joker(name: str):
    return SimpleNamespace(name=name)


def _card(rank="2", enhancement=""):
    return SimpleNamespace(rank=rank, enhancement=enhancement)


def _state(*, jokers=(), deck=()):
    return SimpleNamespace(jokers=list(jokers), owned_deck=list(deck), deck=list(deck))


def test_no_face_cards_requires_ride_the_bus():
    deck = tuple(_card(rank="2") for _ in range(52))
    result = evaluate_no_face_cards_bond(_state(deck=deck))
    assert result.rank == BondRank.LOCKED
    assert result.contribution == 0.0


def test_ride_the_bus_establishes_no_face_cards_bond():
    result = evaluate_no_face_cards_bond(_state(jokers=(_joker("Ride the Bus"),)))
    assert result.contribution == 14.0
    assert result.rank == BondRank.R5


def test_standard_face_density_keeps_ride_the_bus_at_r1():
    deck = tuple([_card(rank="J") for _ in range(4)] + [_card(rank="Q") for _ in range(4)] + [_card(rank="K") for _ in range(4)] + [_card(rank="2") for _ in range(40)])
    result = evaluate_no_face_cards_bond(_state(jokers=(_joker("Ride the Bus"),), deck=deck))
    assert result.contribution == 7.0
    assert result.rank == BondRank.R1


def test_face_depletion_progressively_develops_bond():
    six_faces = tuple([_card(rank="J") for _ in range(2)] + [_card(rank="Q") for _ in range(2)] + [_card(rank="K") for _ in range(2)] + [_card(rank="2") for _ in range(46)])
    result = evaluate_no_face_cards_bond(_state(jokers=(_joker("Ride the Bus"),), deck=six_faces))
    assert result.contribution == 10.0
    assert result.rank == BondRank.R3


def test_zero_natural_faces_is_capstone_support():
    deck = tuple(_card(rank="2") for _ in range(52))
    result = evaluate_no_face_cards_bond(_state(jokers=(_joker("Ride the Bus"),), deck=deck))
    assert result.contribution == 14.0
    assert result.rank == BondRank.R5
