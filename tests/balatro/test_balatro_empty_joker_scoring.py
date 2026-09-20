import pytest

from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.abstract_joker import AbstractJoker
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


def _state(jokers):
    played = BalatroCard("A", "Spades", enhancement="Bonus", seal="Red")
    held = BalatroCard("K", "Hearts", enhancement="Steel")
    state = BalatroState()
    state.hand = [played, held]
    state.jokers = jokers
    state.hand_play_counts[PokerHand.HIGH_CARD.value] = 3
    return state, played


@pytest.mark.parametrize("empty_jokers", [[], ()])
def test_exact_empty_joker_inventory_skips_unused_hand_history_context(
    monkeypatch,
    empty_jokers,
):
    state, played = _state(empty_jokers)
    scorer = BalatroScorer()
    expected = scorer.score(
        PokerHand.HIGH_CARD,
        state,
        [played],
        include_card_chips=True,
        resolve_random_effects=False,
    )

    def fail_if_called(_state):
        raise AssertionError("empty Joker scoring must not build Joker-only context")

    monkeypatch.setattr(scorer, "most_played_hands", fail_if_called)

    assert scorer.score(
        PokerHand.HIGH_CARD,
        state,
        [played],
        include_card_chips=True,
        resolve_random_effects=False,
    ) == expected


def test_joker_inventory_retains_hand_history_context(monkeypatch):
    state, played = _state([AbstractJoker()])
    scorer = BalatroScorer()
    calls = []
    original = scorer.most_played_hands

    def recorded(current_state):
        calls.append(current_state)
        return original(current_state)

    monkeypatch.setattr(scorer, "most_played_hands", recorded)

    scorer.score(PokerHand.HIGH_CARD, state, [played], include_card_chips=True)

    assert calls == [state]


def test_malformed_joker_inventory_does_not_enter_empty_fast_path():
    state, played = _state(None)

    with pytest.raises(TypeError):
        BalatroScorer().score(
            PokerHand.HIGH_CARD,
            state,
            [played],
            include_card_chips=True,
        )
