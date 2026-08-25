from __future__ import annotations

import games.balatro  # install package-level live authorities

from games.balatro.actions import BalatroAction, DISCARD_CARDS
from games.balatro.card import BalatroCard
from games.balatro.live.hand_action_planner_core import D1LiveBlindClearPlanner
from games.balatro.state import BalatroState


def _state() -> BalatroState:
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hands_remaining = 4
    state.discards_remaining = 3
    state.consumable_slots = 2
    state.consumables = []
    return state


def _card(rank: str, suit: str, *, seal: str | None = None) -> BalatroCard:
    card = BalatroCard(rank, suit)
    card.seal = seal
    return card


def test_child_discard_candidates_preserve_purple_seal_trigger_branch() -> None:
    state = _state()
    purple = _card("A", "Spades", seal="Purple")
    state.hand = [
        purple,
        _card("2", "Hearts"),
        _card("3", "Clubs"),
        _card("4", "Diamonds"),
    ]

    candidates = D1LiveBlindClearPlanner()._child_discard_candidates(state)

    assert any(action.cards == [purple] for action in candidates)


def test_full_consumable_capacity_does_not_create_special_purple_branch() -> None:
    state = _state()
    state.consumables = [object(), object()]
    purple = _card("A", "Spades", seal="Purple")
    state.hand = [
        purple,
        _card("2", "Hearts"),
        _card("3", "Clubs"),
        _card("4", "Diamonds"),
    ]

    candidates = D1LiveBlindClearPlanner()._child_discard_candidates(state)

    # The ordinary low-card child generator should not manufacture a Purple-Seal
    # singleton when its Tarot trigger cannot resolve because capacity is full.
    assert not any(action.cards == [purple] for action in candidates)


def test_bounded_discard_beam_reserves_one_purple_trigger_branch() -> None:
    state = _state()
    purple = _card("A", "Spades", seal="Purple")
    low = _card("2", "Hearts")
    other = _card("3", "Clubs")
    state.hand = [purple, low, other]

    purple_action = BalatroAction(DISCARD_CARDS, cards=[purple])
    ordinary_single = BalatroAction(DISCARD_CARDS, cards=[low])
    ordinary_double = BalatroAction(DISCARD_CARDS, cards=[low, other])

    planner = D1LiveBlindClearPlanner()
    # Force the underlying generic beam to prefer ordinary redraws. The installed
    # Purple policy should still retain one mechanically distinct trigger branch;
    # this does not make it the final expectimax winner.
    planner._discard_priority = lambda _state, action: (
        0 if purple in action.cards else 100,
        len(action.cards),
    )

    chosen = planner._diverse_discard_beam(
        state,
        [purple_action, ordinary_single, ordinary_double],
        2,
    )

    assert purple_action in chosen
    assert len(chosen) == 2


def test_terminal_value_carries_projected_purple_tarot() -> None:
    state = _state()
    purple = _card("A", "Spades", seal="Purple")
    state.hand = [purple, _card("2", "Hearts")]

    planner = D1LiveBlindClearPlanner()
    projected = planner.discard_joker_projector.project(state, [purple])
    value = planner._terminal_value(projected, clear=False)

    assert len(projected.consumables) == 1
    assert value.expected_consumables == 1.0
