from types import SimpleNamespace

from games.balatro.bonds import (
    BondRank,
    evaluate_jacks_bond,
    evaluate_kings_bond,
    evaluate_planet_bond,
    evaluate_queens_bond,
    evaluate_tarot_bond,
)


def _joker(name: str):
    return SimpleNamespace(name=name)


def _voucher(name: str):
    return SimpleNamespace(name=name)


def _card(*, rank="2", seal=""):
    return SimpleNamespace(rank=rank, seal=seal)


def _state(*, jokers=(), vouchers=(), deck=()):
    return SimpleNamespace(
        jokers=list(jokers),
        vouchers=list(vouchers),
        owned_deck=list(deck),
        deck=list(deck),
    )


def test_kings_can_emerge_from_baron_or_density():
    baron = evaluate_kings_bond(_state(jokers=(_joker("Baron"),)))
    assert baron.rank == BondRank.R1
    density = evaluate_kings_bond(_state(deck=tuple(_card(rank="K") for _ in range(9))))
    assert density.rank == BondRank.R1


def test_queens_are_independent_of_kings():
    result = evaluate_queens_bond(_state(jokers=(_joker("Shoot the Moon"),)))
    assert result.rank == BondRank.R1
    assert result.target == "Q"


def test_jacks_hit_the_road_is_major_jack_support():
    result = evaluate_jacks_bond(_state(jokers=(_joker("Hit the Road"),)))
    assert result.contribution == 7.0
    assert result.rank == BondRank.R1


def test_tarot_has_multiple_independent_infrastructure_paths():
    cartomancer = evaluate_tarot_bond(_state(jokers=(_joker("Cartomancer"),)))
    merchant = evaluate_tarot_bond(_state(vouchers=(_voucher("Tarot Merchant"),)))
    assert cartomancer.rank == BondRank.R1
    assert merchant.rank == BondRank.R1


def test_planet_telescope_and_blue_seals_share_one_pool():
    result = evaluate_planet_bond(
        _state(
            vouchers=(_voucher("Telescope"),),
            deck=tuple(_card(seal="Blue") for _ in range(4)),
        )
    )
    assert result.contribution == 10.0
    assert result.rank == BondRank.R2
