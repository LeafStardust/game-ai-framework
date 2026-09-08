from types import SimpleNamespace

import games.balatro  # noqa: F401 - initializes production stack
from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy
from games.balatro.target_hand_engine_policy import _safe_target_play, _target_hands


def test_runner_declares_straight_targets():
    state = SimpleNamespace(jokers=[SimpleNamespace(label="Runner")])
    assert _target_hands(state) == ("STRAIGHT", "STRAIGHT_FLUSH")


def test_to_do_list_uses_public_current_target():
    state = SimpleNamespace(
        jokers=[SimpleNamespace(label="To Do List", public_state={"target_hand": "Straight"})]
    )
    assert _target_hands(state) == ("STRAIGHT",)


def test_safe_target_play_can_replace_discard_with_runner_straight(monkeypatch):
    straight = SimpleNamespace(
        action=SimpleNamespace(name=PLAY_CARDS, cards=(SimpleNamespace(rank="4"),)),
        value=SimpleNamespace(clear_probability=0.90),
    )
    pair = SimpleNamespace(
        action=SimpleNamespace(name=PLAY_CARDS, cards=(SimpleNamespace(rank="5"),)),
        value=SimpleNamespace(clear_probability=0.91),
    )
    policy = SimpleNamespace(
        EPSILON=1e-9,
        evaluator=SimpleNamespace(
            project_play=lambda _state, _action: SimpleNamespace(expected_hand_score=120.0)
        ),
        _hand_evaluator=SimpleNamespace(
            evaluate=lambda cards, **_kwargs: SimpleNamespace(value="STRAIGHT" if cards[0].rank == "4" else "PAIR")
        ),
        _strategy_fit=lambda _state, _action: (1.0,),
        _within_type_key=lambda _plan: (0,),
    )
    decision = SimpleNamespace(
        action=SimpleNamespace(name=DISCARD_CARDS, cards=()),
        selected_plan=pair,
        thresholds=SimpleNamespace(safe_clear_probability_tolerance=0.02),
        pace_target=100.0,
    )
    state = SimpleNamespace(jokers=[SimpleNamespace(label="Runner")])
    selected = _safe_target_play(policy, state, (pair, straight), decision)
    assert selected is not None
    assert selected[2] is straight


def test_production_stack_does_not_install_target_hand_guard():
    assert not hasattr(
        StrategyAwareLiveHandActionPolicy,
        "_target_hand_engine_policy_installed",
    )
