import pytest

from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.abstract_joker import AbstractJoker
from games.balatro.live.final_joker_outcomes import (
    LiveFinalJokerScoreOutcomeModel,
)
from games.balatro.live.score_outcomes import (
    ScoreOutcome,
    ScoreOutcomeDistribution,
    ScoreProjectionTransition,
)
from games.balatro.state import BalatroState


def _deterministic_state():
    played = BalatroCard(
        "A",
        "Spades",
        enhancement="Bonus",
        edition="Foil",
        seal="Red",
    )
    held = BalatroCard("K", "Hearts", enhancement="Steel")
    state = BalatroState()
    state.hand = [played, held]
    state.deck = []
    state.owned_deck = list(state.hand)
    state.hand_levels[PokerHand.HIGH_CARD.value] = 3
    state.jokers = []
    state.boss_name = None
    return state, played


@pytest.mark.parametrize("include_card_chips", [True, False])
def test_score_distribution_only_matches_full_deterministic_transition(
    monkeypatch,
    include_card_chips,
):
    state, played = _deterministic_state()
    model = LiveFinalJokerScoreOutcomeModel()
    expected = model.project_transition(
        PokerHand.HIGH_CARD,
        state,
        [played],
        include_card_chips=include_card_chips,
    ).distribution

    def fail_transition(*_args, **_kwargs):
        raise AssertionError("exact score-only projection must not build transition state")

    monkeypatch.setattr(model, "project_transition", fail_transition)
    actual = model.project(
        PokerHand.HIGH_CARD,
        state,
        [played],
        include_card_chips=include_card_chips,
    )

    assert actual == expected
    assert actual.deterministic
    assert state.round_hand_play_counts[PokerHand.HIGH_CARD.value] == 0


@pytest.mark.parametrize("unsupported", ["joker", "boss", "lucky", "glass"])
def test_score_distribution_only_falls_back_for_stateful_or_random_mechanics(
    monkeypatch,
    unsupported,
):
    state, played = _deterministic_state()
    if unsupported == "joker":
        state.jokers = [AbstractJoker()]
    elif unsupported == "boss":
        state.boss_name = "The Flint"
    else:
        played.enhancement = unsupported.title()

    sentinel = ScoreOutcomeDistribution((ScoreOutcome(123, 1.0),))
    calls = []

    def project_transition(*args, **kwargs):
        calls.append((args, kwargs))
        return ScoreProjectionTransition(sentinel, state)

    model = LiveFinalJokerScoreOutcomeModel()
    monkeypatch.setattr(model, "project_transition", project_transition)

    assert model.project(PokerHand.HIGH_CARD, state, [played]) is sentinel
    assert len(calls) == 1
