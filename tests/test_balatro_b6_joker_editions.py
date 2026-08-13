import pytest

from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.egg import EggJoker
from games.balatro.jokers.green_joker import GreenJoker
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


def _state():
    ace = BalatroCard("A", "Spades", live_id=1)
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [ace]
    return state, ace


@pytest.mark.parametrize(
    ("edition", "expected"),
    [
        ("FOIL", 66),
        ("HOLO", 176),
        ("HOLOGRAPHIC", 176),
        ("POLYCHROME", 24),
        ("NEGATIVE", 16),
        (None, 16),
    ],
)
def test_base_scorer_applies_joker_editions(edition, expected):
    state, ace = _state()
    joker = EggJoker()
    joker.edition = edition
    state.jokers = [joker]

    score = BalatroScorer().score(
        PokerHand.HIGH_CARD,
        state=state,
        cards=[ace],
        include_card_chips=True,
        resolve_random_effects=False,
    )

    assert score.total == expected


def test_joker_edition_is_applied_after_its_own_scoring_effect():
    state, ace = _state()
    green = GreenJoker()
    green.mult = 4
    green.edition = "POLYCHROME"
    state.jokers = [green]

    score = BalatroScorer().score(
        PokerHand.HIGH_CARD,
        state=state,
        cards=[ace],
        include_card_chips=True,
        resolve_random_effects=False,
    )

    # 16 Chips; Green grows 4 -> 5 and adds 5 Mult to the base 1, then
    # Polychrome applies x1.5: 16 * 6 * 1.5 = 144.
    assert score.total == 144
    assert green.mult == 5


@pytest.mark.parametrize(
    ("edition", "expected"),
    [
        ("FOIL", 66),
        ("HOLO", 176),
        ("POLYCHROME", 24),
    ],
)
def test_live_joker_projector_carries_hydrated_editions_without_mutating_observed_joker(
    edition,
    expected,
):
    state, ace = _state()
    joker = EggJoker()
    joker.edition = edition
    state.jokers = [joker]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.HIGH_CARD,
        state,
        [ace],
    )

    assert transition.distribution.minimum == expected
    assert transition.distribution.maximum == expected
    assert transition.joker_projection_complete is True
    assert joker.edition == edition
    assert transition.state_after_scoring.jokers[0] is not joker
    assert transition.state_after_scoring.jokers[0].edition == edition
