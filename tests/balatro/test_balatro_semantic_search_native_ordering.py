from types import SimpleNamespace

import games.balatro  # noqa: F401 - initialize production registration
from games.balatro.actions import BalatroAction, DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.blind_clear_planner import (
    LiveBlindClearPlanner,
    LiveBlindPlan,
    LiveBlindPlanValue,
    _ActionEstimate,
)
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


def _value(*, clear=0.0, progress=0.0, score=0.0, hands=1.0, discards=0.0):
    return LiveBlindPlanValue(
        clear_probability=clear,
        expected_progress=progress,
        expected_score=score,
        expected_hands_remaining=hands,
        expected_discards_remaining=discards,
        expected_consumables=0.0,
    )


def _plan(action, value, *, exact):
    return LiveBlindPlan(
        action=action,
        value=value,
        horizon=2,
        exact=exact,
        candidate_count=2,
    )


def test_native_estimate_key_prefers_better_sampled_discard_recovery_over_exactness():
    exact = _ActionEstimate(
        BalatroAction(DISCARD_CARDS, cards=[SimpleNamespace(rank="2")]),
        _value(progress=0.20, score=20.0),
        True,
    )
    sampled = _ActionEstimate(
        BalatroAction(DISCARD_CARDS, cards=[SimpleNamespace(rank="3")]),
        _value(progress=0.35, score=35.0),
        False,
    )

    assert LiveBlindClearPlanner._estimate_key(sampled) > LiveBlindClearPlanner._estimate_key(exact)


def test_native_estimate_key_keeps_shorter_guaranteed_play_clear_when_values_tie():
    short = _ActionEstimate(
        BalatroAction(PLAY_CARDS, cards=[SimpleNamespace(rank="A")]),
        _value(clear=1.0, progress=1.0, score=100.0),
        True,
    )
    long = _ActionEstimate(
        BalatroAction(
            PLAY_CARDS,
            cards=[SimpleNamespace(rank="A"), SimpleNamespace(rank="K")],
        ),
        _value(clear=1.0, progress=1.0, score=100.0),
        True,
    )

    assert LiveBlindClearPlanner._estimate_key(short) > LiveBlindClearPlanner._estimate_key(long)


def test_native_strategy_ordering_prefers_meaningful_redraw_when_signal_is_zero():
    policy = StrategyAwareLiveHandActionPolicy()
    one = _plan(
        BalatroAction(DISCARD_CARDS, cards=[SimpleNamespace(rank="2")]),
        _value(),
        exact=True,
    )
    wide = _plan(
        BalatroAction(
            DISCARD_CARDS,
            cards=[
                SimpleNamespace(rank="2"),
                SimpleNamespace(rank="3"),
                SimpleNamespace(rank="4"),
            ],
        ),
        _value(),
        exact=True,
    )

    assert policy._within_type_key(wide) > policy._within_type_key(one)


def test_production_stack_does_not_install_semantic_search_overlay():
    assert not hasattr(LiveBlindClearPlanner, "_semantic_search_guard_installed")
    assert LiveBlindClearPlanner._estimate_key.__module__ == (
        "games.balatro.live.blind_clear_planner"
    )
    assert StrategyAwareLiveHandActionPolicy._within_type_key.__module__ == (
        "games.balatro.live.strategy_hand_policy"
    )
