from types import SimpleNamespace

from games.balatro.bonds import evaluate_kings_bond
from games.balatro.bonds.model import BondRank


def _card(rank="K", enhancement=""):
    return SimpleNamespace(rank=rank, enhancement=enhancement)


def test_hidden_stone_ranks_do_not_establish_kings_density():
    state = SimpleNamespace(
        jokers=[],
        owned_deck=[_card(enhancement="Stone") for _ in range(20)],
        deck=[],
    )
    result = evaluate_kings_bond(state)
    assert result.contribution == 0.0
    assert result.rank == BondRank.R0


def test_non_stone_kings_still_establish_rank_density():
    state = SimpleNamespace(
        jokers=[],
        owned_deck=[_card() for _ in range(6)],
        deck=[],
    )
    result = evaluate_kings_bond(state)
    assert result.contribution == 3.0
    assert result.rank == BondRank.R0
