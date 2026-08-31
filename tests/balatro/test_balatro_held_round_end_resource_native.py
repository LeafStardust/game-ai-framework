from types import SimpleNamespace

import games.balatro  # noqa: F401 - initialize the production stack
from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.card import BalatroCard
from games.balatro.live.blind_clear_planner import (
    LiveBlindClearPlanner,
    _ActionEstimate,
)
from games.balatro.live.hand_action_planner import (
    D1LiveBlindClearPlanner as IntegratedD1LiveBlindClearPlanner,
)
from games.balatro.live.hand_action_planner_core import (
    D1LiveBlindClearPlanner as CoreD1LiveBlindClearPlanner,
)


class _TerminalPlanner(LiveBlindClearPlanner):
    def _estimate_play(self, state, action, depth):
        del depth
        return _ActionEstimate(
            action,
            self._terminal_value(state, clear=True),
            True,
        )


class _EqualProjectionEvaluator:
    def project_play(self, _state, _action):
        return SimpleNamespace(
            clear_probability=1.0,
            expected_hand_score=100.0,
            hand_score=100,
        )


def _state(hand, *, consumable_slots=2, consumables=()):
    return SimpleNamespace(
        hand=list(hand),
        consumable_slots=consumable_slots,
        consumables=list(consumables),
        score=100,
        hands_remaining=0,
        discards_remaining=1,
        blind=SimpleNamespace(requirement=100),
        jokers=[],
    )


def test_native_terminal_value_counts_blue_seal_left_held_on_clear():
    played = BalatroCard("2", "Clubs", live_id=1)
    blue = BalatroCard("3", "Diamonds", seal="Blue", live_id=2)
    state = _state([played, blue])
    action = BalatroAction(PLAY_CARDS, cards=[played])

    estimate = _TerminalPlanner()._estimate_action(state, action, depth=1)

    assert estimate.value.expected_consumables == 1.0


def test_native_terminal_value_does_not_reward_blue_seal_that_was_played():
    blue = BalatroCard("3", "Diamonds", seal="Blue", live_id=2)
    held = BalatroCard("2", "Clubs", live_id=1)
    state = _state([blue, held])
    action = BalatroAction(PLAY_CARDS, cards=[blue])

    estimate = _TerminalPlanner()._estimate_action(state, action, depth=1)

    assert estimate.value.expected_consumables == 0.0


def test_native_terminal_value_respects_consumable_capacity():
    played = BalatroCard("2", "Clubs", live_id=1)
    blue = BalatroCard("3", "Diamonds", seal="Blue", live_id=2)
    state = _state(
        [played, blue],
        consumable_slots=1,
        consumables=[SimpleNamespace(name="The Fool")],
    )
    action = BalatroAction(PLAY_CARDS, cards=[played])

    estimate = _TerminalPlanner()._estimate_action(state, action, depth=1)

    assert estimate.value.expected_consumables == 1.0


def test_native_play_priority_preserves_gold_when_other_fields_tie():
    planner = LiveBlindClearPlanner(evaluator=_EqualProjectionEvaluator())
    gold = BalatroCard("2", "Clubs", enhancement="Gold")
    plain = BalatroCard("3", "Diamonds")

    play_gold = BalatroAction(PLAY_CARDS, cards=[gold])
    keep_gold = BalatroAction(PLAY_CARDS, cards=[plain])

    assert planner._play_priority(None, keep_gold) > planner._play_priority(None, play_gold)


def test_production_stack_does_not_install_held_round_end_resource_overlay():
    for planner_type in (
        LiveBlindClearPlanner,
        CoreD1LiveBlindClearPlanner,
        IntegratedD1LiveBlindClearPlanner,
    ):
        assert not hasattr(
            planner_type,
            "_held_round_end_resource_policy_installed",
        )
