from __future__ import annotations

from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.live.boss_score_transform import BossBaseScoreScorerMixin
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


class _BossAwareScorer(BossBaseScoreScorerMixin, BalatroScorer):
    pass


def _psychic_state() -> BalatroState:
    state = BalatroState()
    state.boss_name = "The Psychic"
    state.jokers = []
    state.hand_levels = {}
    return state


def test_psychic_short_play_is_legal_to_project_but_scores_zero() -> None:
    cards = [
        BalatroCard("8", "Hearts"),
        BalatroCard("8", "Spades"),
    ]

    score = _BossAwareScorer().score(
        PokerHand.PAIR,
        state=_psychic_state(),
        cards=cards,
        include_card_chips=True,
        resolve_random_effects=False,
    )

    assert score.total == 0
    assert score.chips == 0
    assert score.mult == 0


def test_psychic_five_card_play_scores_normally() -> None:
    cards = [
        BalatroCard("8", "Hearts"),
        BalatroCard("8", "Spades"),
        BalatroCard("K", "Clubs"),
        BalatroCard("7", "Diamonds"),
        BalatroCard("2", "Hearts"),
    ]

    score = _BossAwareScorer().score(
        PokerHand.PAIR,
        state=_psychic_state(),
        cards=cards,
        include_card_chips=True,
        resolve_random_effects=False,
    )

    assert score.total > 0
