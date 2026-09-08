from __future__ import annotations

from games.balatro.card import BalatroCard
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.burnt_joker import BurntJoker
from games.balatro.jokers.green_joker import GreenJoker
from games.balatro.live.discard_projection import LiveDiscardJokerProjector
from games.balatro.state import BalatroState


def _state() -> BalatroState:
    state = BalatroState()
    state.discards_used = 0
    state.discard_pile = []
    return state


def test_player_discard_still_activates_burnt_joker_once() -> None:
    state = _state()
    state.jokers = [BurntJoker()]
    card = BalatroCard("A", "Spades", live_id="ace")

    projected = LiveDiscardJokerProjector().project(
        state,
        [card],
        consume_discard_use=True,
    )

    assert projected.discards_used == 1
    assert projected.hand_levels["HIGH_CARD"] == 2

    second = LiveDiscardJokerProjector().project(
        projected,
        [BalatroCard("K", "Hearts", live_id="king")],
        consume_discard_use=True,
    )
    assert second.hand_levels["HIGH_CARD"] == 2


def test_hook_forced_discard_does_not_activate_burnt_joker() -> None:
    state = _state()
    state.jokers = [BurntJoker()]

    projected = LiveDiscardJokerProjector().project(
        state,
        [BalatroCard("A", "Spades", live_id="ace")],
        consume_discard_use=False,
    )

    assert projected.discards_used == 0
    assert projected.hand_levels["HIGH_CARD"] == 1


def test_hook_forced_discard_does_not_activate_blueprint_copying_burnt() -> None:
    state = _state()
    state.jokers = [BlueprintJoker(), BurntJoker()]

    projected = LiveDiscardJokerProjector().project(
        state,
        [BalatroCard("A", "Spades", live_id="ace")],
        consume_discard_use=False,
    )

    assert projected.hand_levels["HIGH_CARD"] == 1


def test_hook_forced_discard_still_penalizes_green_joker_without_using_discard() -> None:
    state = _state()
    green = GreenJoker()
    green.mult = 4
    state.jokers = [green]

    projected = LiveDiscardJokerProjector().project(
        state,
        [BalatroCard("2", "Clubs", live_id="two")],
        consume_discard_use=False,
    )

    assert projected.discards_used == 0
    assert projected.jokers[0].mult == 3
    assert state.jokers[0].mult == 4
