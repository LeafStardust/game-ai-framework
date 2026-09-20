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


@pytest.mark.parametrize("empty_jokers", [[], ()])
def test_empty_joker_held_phase_preserves_steel_retriggers(empty_jokers):
    state, played = _state(empty_jokers)
    state.hand[1].seal = "Red"

    score = BalatroScorer().score(
        PokerHand.HIGH_CARD,
        state,
        [played],
        include_card_chips=True,
        resolve_random_effects=False,
        joker_data={"retrigger_held_abilities": 2},
    )

    assert score.mult == pytest.approx(5.0625)
    assert score.x_mult == 1.0


def test_empty_joker_plain_held_cards_skip_held_trigger_context(monkeypatch):
    state, played = _state([])
    state.hand[1].enhancement = None
    scorer = BalatroScorer()

    def unexpected(*args, **kwargs):
        raise AssertionError("plain held cards have no empty-Joker scoring effect")

    monkeypatch.setattr(scorer, "_held_card_trigger_count", unexpected)

    scorer.score(
        PokerHand.HIGH_CARD,
        state,
        [played],
        include_card_chips=True,
        resolve_random_effects=False,
    )


def test_malformed_joker_inventory_does_not_enter_empty_fast_path():
    state, played = _state(None)

    with pytest.raises(TypeError):
        BalatroScorer().score(
            PokerHand.HIGH_CARD,
            state,
            [played],
            include_card_chips=True,
        )
