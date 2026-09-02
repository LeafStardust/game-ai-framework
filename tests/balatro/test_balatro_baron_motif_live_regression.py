from types import SimpleNamespace

from games.balatro.bonds.motifs import MotifState, evaluate_baron_mime_steel


def _card(rank: str, enhancement: str = ""):
    return SimpleNamespace(rank=rank, enhancement=enhancement)


def _standard_rank_counts():
    ranks = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
    return [_card(rank) for rank in ranks for _ in range(4)]


def test_baron_plus_untouched_four_kings_is_not_exceptional_motif_potential():
    state = SimpleNamespace(
        jokers=(SimpleNamespace(name="Baron"),),
        owned_deck=_standard_rank_counts(),
    )

    motif = evaluate_baron_mime_steel(state, ())

    assert motif.state == MotifState.ABSENT
    assert "BARON" in motif.present_components
    assert "KING_INFRASTRUCTURE" in motif.missing_components


def test_baron_plus_increased_king_density_can_become_motif_potential():
    deck = _standard_rank_counts()
    deck.append(_card("K"))
    state = SimpleNamespace(
        jokers=(SimpleNamespace(name="Baron"),),
        owned_deck=deck,
    )

    motif = evaluate_baron_mime_steel(state, ())

    assert motif.state == MotifState.POTENTIAL
    assert "KING_INFRASTRUCTURE" in motif.present_components
