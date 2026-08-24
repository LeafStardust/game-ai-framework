from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.castle_discard_policy import _safe_castle_discard_alternative


def _plan(action, *, probability=0.5, expected_score=100.0, exact=True):
    return SimpleNamespace(
        action=action,
        value=SimpleNamespace(
            clear_probability=probability,
            expected_score=expected_score,
        ),
        exact=exact,
    )


def test_castle_redirects_only_to_near_equivalent_castle_suit_discard():
    selected = _plan(
        BalatroAction(DISCARD_CARDS, cards=[BalatroCard("Q", "Spades")]),
        probability=0.50,
        expected_score=100.0,
    )
    castle = _plan(
        BalatroAction(DISCARD_CARDS, cards=[BalatroCard("4", "Diamonds")]),
        probability=0.49,
        expected_score=95.0,
    )
    result = SimpleNamespace(selected_plan=selected, plans=(selected, castle))
    assert _safe_castle_discard_alternative(result, "Diamonds") is castle


def test_castle_never_forces_discard_or_accepts_material_survival_loss():
    play = _plan(BalatroAction(PLAY_CARDS, cards=[BalatroCard("A", "Hearts")]))
    castle = _plan(
        BalatroAction(DISCARD_CARDS, cards=[BalatroCard("4", "Diamonds")]),
        probability=0.50,
        expected_score=100.0,
    )
    result = SimpleNamespace(selected_plan=play, plans=(play, castle))
    assert _safe_castle_discard_alternative(result, "Diamonds") is None

    selected = _plan(
        BalatroAction(DISCARD_CARDS, cards=[BalatroCard("Q", "Spades")]),
        probability=0.60,
        expected_score=100.0,
    )
    bad_castle = _plan(
        BalatroAction(DISCARD_CARDS, cards=[BalatroCard("4", "Diamonds")]),
        probability=0.50,
        expected_score=70.0,
    )
    result = SimpleNamespace(selected_plan=selected, plans=(selected, bad_castle))
    assert _safe_castle_discard_alternative(result, "Diamonds") is None
