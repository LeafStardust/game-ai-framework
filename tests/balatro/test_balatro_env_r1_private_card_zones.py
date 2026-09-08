import pytest

from games.balatro.card import BalatroCard
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _state() -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.money = 0
    state.hand_size = 8
    state.hands_remaining = 4
    state.discards_remaining = 3
    state.joker_slots = 5
    state.consumable_slots = 2
    return state


@pytest.mark.parametrize("zone_name", ("draw_pile", "discard_pile", "played_pile"))
def test_balatro_env_r1_private_card_zones_require_lists(zone_name):
    kwargs = {zone_name: (BalatroCard("A", "Spades"),)}

    with pytest.raises(HeadlessTransitionError, match=f"{zone_name} must be a list"):
        HeadlessRunState(public=_state(), seed=43, **kwargs)


@pytest.mark.parametrize("zone_name", ("draw_pile", "discard_pile", "played_pile"))
def test_balatro_env_r1_private_card_zones_require_balatro_cards(zone_name):
    kwargs = {zone_name: [BalatroCard("A", "Spades"), "not-a-card"]}

    with pytest.raises(
        HeadlessTransitionError,
        match=f"{zone_name} must contain only BalatroCard values",
    ):
        HeadlessRunState(public=_state(), seed=44, **kwargs)


def test_balatro_env_r1_private_card_zones_accept_exact_balatro_cards():
    draw = [BalatroCard("A", "Spades")]
    discard = [BalatroCard("K", "Hearts")]
    played = [BalatroCard("Q", "Clubs")]

    run = HeadlessRunState(
        public=_state(),
        seed=45,
        draw_pile=draw,
        discard_pile=discard,
        played_pile=played,
    )

    assert run.draw_pile == draw
    assert run.discard_pile == discard
    assert run.played_pile == played
