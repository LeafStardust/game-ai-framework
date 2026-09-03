from time import perf_counter

import pytest

import games.balatro.live.hand_action_planner_core as planner_module
from games.balatro.card import BalatroCard
from games.balatro.live.blind_clear_planner import PlannerSearchBudgetExceeded
from games.balatro.live.consumable_escape import (
    SunConsumableEscapePlanner,
    judgement_live_block_reason,
)
from games.balatro.live.hand_action_planner_core import D1LiveBlindClearPlanner
from games.balatro.state import BalatroState
from games.balatro.tarots import create_tarot


def test_sun_targets_only_meaningful_non_heart_cards():
    state = BalatroState()
    state.hand = [
        BalatroCard("K", "Spades"),
        BalatroCard("Q", "Hearts"),
        BalatroCard("J", "Clubs"),
        BalatroCard("10", "Diamonds", enhancement="Wild"),
        BalatroCard("9", "Spades", enhancement="Stone"),
    ]

    targets = SunConsumableEscapePlanner._target_sets(state)

    assert targets == ((0,), (2,), (0, 2))


def test_apply_sun_isolated_from_authoritative_state():
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [
        BalatroCard("K", "Spades", live_id=1),
        BalatroCard("Q", "Diamonds", live_id=2),
        BalatroCard("J", "Hearts", live_id=3),
    ]
    state.consumables = [create_tarot("The Sun"), create_tarot("Judgement")]

    transformed = SunConsumableEscapePlanner._apply_sun(state, (0, 1), 0)

    assert [card.suit for card in transformed.hand] == [
        "Hearts",
        "Hearts",
        "Hearts",
    ]
    assert [card.suit for card in state.hand] == [
        "Spades",
        "Diamonds",
        "Hearts",
    ]
    assert [item.name for item in transformed.consumables] == ["Judgement"]
    assert [item.name for item in state.consumables] == ["The Sun", "Judgement"]


def test_sun_escape_respects_an_expired_parent_d1_deadline():
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [
        BalatroCard("K", "Spades"),
        BalatroCard("Q", "Diamonds"),
        BalatroCard("J", "Hearts"),
    ]
    state.consumables = [create_tarot("The Sun")]
    planner = SunConsumableEscapePlanner(
        horizon=2,
        deadline=perf_counter() - 1.0,
    )

    with pytest.raises(PlannerSearchBudgetExceeded, match="parent D1 wall-clock budget"):
        planner.plan(state)


def test_sun_root_proof_cannot_consume_the_entire_d1_deadline(monkeypatch):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [
        BalatroCard("K", "Spades"),
        BalatroCard("Q", "Diamonds"),
        BalatroCard("J", "Hearts"),
    ]
    state.consumables = [create_tarot("The Sun")]

    observed = {}

    class _SlowSunProof:
        def __init__(self, **kwargs):
            observed["deadline"] = kwargs["deadline"]

        def plan(self, current):
            assert current is state
            raise RuntimeError("bounded Sun proof expired")

    monkeypatch.setattr(planner_module, "perf_counter", lambda: 100.0)
    monkeypatch.setattr(planner_module, "SunConsumableEscapePlanner", _SlowSunProof)
    planner = D1LiveBlindClearPlanner(deadline=107.0)

    assert planner._guaranteed_sun_action(state) is None
    assert observed["deadline"] == pytest.approx(
        100.0 + planner._SUN_ROOT_PROOF_SECONDS
    )
    assert observed["deadline"] < planner.deadline


def test_judgement_is_explicitly_blocked_for_live_blind_planning():
    state = BalatroState()
    state.consumables = [create_tarot("Judgement")]

    reason = judgement_live_block_reason(state)

    assert reason is not None
    assert "random" in reason
    assert "full Joker pool" in reason


def test_judgement_block_reason_absent_when_not_held():
    state = BalatroState()
    state.consumables = [create_tarot("The Sun")]

    assert judgement_live_block_reason(state) is None
