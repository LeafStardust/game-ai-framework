from types import SimpleNamespace

from games.balatro.bonds import evaluate_low_ranks_bond
from games.balatro.bonds.model import BondRealization
from games.balatro.bonds.realization import realize_bond


def _joker(name):
    return SimpleNamespace(name=name)


def _card(rank):
    return SimpleNamespace(rank=str(rank), suit="Hearts", enhancement="")


def _state(joker, ranks):
    played = [_card(rank) for rank in ranks]
    # Keep the Low Ranks Bond structurally established even for minor-only
    # contributors such as Walkie Talkie, so these tests isolate realization
    # semantics rather than R0 -> DORMANT behavior.
    deck = played + [_card("2") for _ in range(max(0, 20 - len(played)))]
    return SimpleNamespace(
        jokers=[_joker(joker)],
        scoring_cards=played,
        played_cards=played,
        current_played_cards=played,
        owned_deck=deck,
        deck=deck,
    )


def test_wee_joker_only_realizes_on_twos():
    assert realize_bond(evaluate_low_ranks_bond(_state("Wee Joker", ["5"])), _state("Wee Joker", ["5"])).realization == BondRealization.PARTIAL
    assert realize_bond(evaluate_low_ranks_bond(_state("Wee Joker", ["2"])), _state("Wee Joker", ["2"])).realization == BondRealization.ACTIVE


def test_even_steven_only_realizes_on_even_low_ranks():
    assert realize_bond(evaluate_low_ranks_bond(_state("Even Steven", ["3"])), _state("Even Steven", ["3"])).realization == BondRealization.PARTIAL
    assert realize_bond(evaluate_low_ranks_bond(_state("Even Steven", ["4"])), _state("Even Steven", ["4"])).realization == BondRealization.ACTIVE


def test_walkie_talkie_low_rank_support_only_realizes_on_four():
    # Walkie also triggers Tens, but Tens are outside the frozen 2-5 Low Ranks Bond.
    assert realize_bond(evaluate_low_ranks_bond(_state("Walkie Talkie", ["2"])), _state("Walkie Talkie", ["2"])).realization == BondRealization.PARTIAL
    assert realize_bond(evaluate_low_ranks_bond(_state("Walkie Talkie", ["4"])), _state("Walkie Talkie", ["4"])).realization == BondRealization.ACTIVE


def test_fibonacci_low_rank_support_excludes_four():
    assert realize_bond(evaluate_low_ranks_bond(_state("Fibonacci", ["4"])), _state("Fibonacci", ["4"])).realization == BondRealization.PARTIAL
    assert realize_bond(evaluate_low_ranks_bond(_state("Fibonacci", ["3"])), _state("Fibonacci", ["3"])).realization == BondRealization.ACTIVE
