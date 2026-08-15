from types import SimpleNamespace

from games.balatro.actions import USE_CONSUMABLE
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.live.consumable_timing import HOLD, USE, LiveConsumableTimingPolicy
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.state import BalatroState
from games.balatro.tarots import Hermit, Strength


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


def _strength_clear_state():
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.score = 0
    state.money = 0
    state.hands_remaining = 1
    state.discards_remaining = 0
    state.blind = Blind(BlindType.SMALL, 8)
    card = BalatroCard("2", "Hearts", live_id=0)
    state.hand = [card]
    state.deck = [BalatroCard("2", "Hearts", live_id=10)]
    state.jokers = []
    strength = Strength()
    strength.live_id = 100
    state.consumables = [strength]
    state.consumable_slots = 2
    return state, card, strength


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


def test_d1_integrates_supported_strength_when_it_proves_guaranteed_clear():
    state, card, strength = _strength_clear_state()
    planner = D1LiveBlindClearPlanner(
        horizon=1,
        play_width=6,
        discard_width=0,
        max_nodes=3000,
    )

    plan = planner.plan(state)

    assert plan.action.name == USE_CONSUMABLE
    assert plan.action.target is strength
    assert plan.action.cards == [card]
    assert plan.value.clear_probability == 1.0
    assert plan.value.expected_score == 8.0
    assert plan.exact is True


def test_default_b6_inventory_defers_guaranteed_clear_consumable_to_d1():
    state, _, strength = _strength_clear_state()
    policy = LiveConsumableTimingPolicy()

    direct = policy.recommend(state, strength)
    inventory = policy.recommend_inventory(state)
    d1_inventory = LiveConsumableTimingPolicy(
        defer_blind_clear_to_d1=False
    ).recommend_inventory(state)

    assert direct.decision == USE
    assert direct.after_projection is not None
    assert direct.after_projection.clears_blind is True
    assert inventory
    assert inventory[0].decision == HOLD
    assert any("delegated to D1" in note for note in inventory[0].rationale)
    assert d1_inventory
    assert d1_inventory[0].decision == USE


def test_default_b6_inventory_keeps_non_clear_economy_timing():
    state, _, _ = _strength_clear_state()
    hermit = Hermit()
    hermit.live_id = 200
    state.money = 10
    state.consumables = [hermit]

    recommendations = LiveConsumableTimingPolicy().recommend_inventory(state)

    assert recommendations
    assert recommendations[0].decision == USE
    assert recommendations[0].to_action() is not None
