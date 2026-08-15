from types import SimpleNamespace

from games.balatro.actions import USE_CONSUMABLE
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.state import BalatroState


def _sun_flush_state(*, boss=False):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.score = 0
    state.money = 0
    state.hands_remaining = 1
    state.discards_remaining = 0
    state.blind = Blind(BlindType.BOSS if boss else BlindType.SMALL, 300)
    state.boss_name = "The Head" if boss else None
    off_suit = BalatroCard("2", "Clubs", live_id=4)
    state.hand = [
        BalatroCard("A", "Hearts", live_id=0),
        BalatroCard("K", "Hearts", live_id=1),
        BalatroCard("Q", "Hearts", live_id=2),
        BalatroCard("J", "Hearts", live_id=3),
        off_suit,
    ]
    state.deck = []
    state.jokers = []
    sun = SimpleNamespace(name="The Sun", live_id=100)
    state.consumables = [sun]
    return state, off_suit, sun


def test_d1_uses_sun_when_it_proves_exact_guaranteed_clear():
    state, off_suit, sun = _sun_flush_state()
    planner = D1LiveBlindClearPlanner(
        horizon=1,
        play_width=6,
        discard_width=0,
        max_nodes=3000,
    )

    plan = planner.plan(state)

    assert plan.action.name == USE_CONSUMABLE
    assert plan.action.target is sun
    assert plan.action.cards == [off_suit]
    assert plan.value.clear_probability == 1.0
    assert plan.exact is True


def test_d1_sun_escape_fails_closed_on_boss_blinds():
    state, _, _ = _sun_flush_state(boss=True)
    planner = D1LiveBlindClearPlanner(
        horizon=1,
        play_width=6,
        discard_width=0,
        max_nodes=3000,
    )

    plan = planner.plan(state)

    assert plan.action.name != USE_CONSUMABLE
