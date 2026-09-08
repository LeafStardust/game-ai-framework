from types import SimpleNamespace

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.strategy_execution_guard_policy import (
    _green_preserving_play,
    realized_banner_delayed_no_discard,
)


def _joker(name):
    return SimpleNamespace(name=name, label=name)


def _plan(action_name, clear_probability, *, expected_score=0.0):
    return SimpleNamespace(
        action=SimpleNamespace(name=action_name, cards=()),
        exact=True,
        value=SimpleNamespace(
            clear_probability=float(clear_probability),
            expected_progress=float(clear_probability),
            expected_hands_remaining=1.0,
            expected_discards_remaining=1.0,
            expected_score=float(expected_score),
        ),
    )


def _decision(selected_plan, tolerance=0.01):
    return SimpleNamespace(
        action=selected_plan.action,
        selected_plan=selected_plan,
        thresholds=SimpleNamespace(safe_clear_probability_tolerance=float(tolerance)),
    )


def test_banner_delayed_is_realized_no_discard_package():
    state = SimpleNamespace(
        jokers=[_joker("Banner"), _joker("Delayed Gratification")],
    )
    assert realized_banner_delayed_no_discard(state) is True


def test_banner_without_delayed_does_not_force_no_discard_preservation():
    state = SimpleNamespace(jokers=[_joker("Banner"), _joker("Scholar")])
    assert realized_banner_delayed_no_discard(state) is False


def test_delayed_without_banner_does_not_force_no_discard_preservation():
    state = SimpleNamespace(jokers=[_joker("Delayed Gratification"), _joker("Sly Joker")])
    assert realized_banner_delayed_no_discard(state) is False


def test_green_joker_prefers_survival_equivalent_play_over_discard():
    play = _plan(PLAY_CARDS, 0.0, expected_score=500.0)
    discard = _plan(DISCARD_CARDS, 0.0)
    policy = SimpleNamespace(EPSILON=1e-12)
    state = SimpleNamespace(jokers=[_joker("Green Joker")])

    selected = _green_preserving_play(
        policy,
        state,
        (play, discard),
        _decision(discard),
    )

    assert selected is play


def test_green_joker_does_not_override_materially_safer_discard():
    play = _plan(PLAY_CARDS, 0.25, expected_score=500.0)
    discard = _plan(DISCARD_CARDS, 0.50)
    policy = SimpleNamespace(EPSILON=1e-12)
    state = SimpleNamespace(jokers=[_joker("Green Joker")])

    selected = _green_preserving_play(
        policy,
        state,
        (play, discard),
        _decision(discard, tolerance=0.01),
    )

    assert selected is None


def test_non_green_build_keeps_canonical_discard():
    play = _plan(PLAY_CARDS, 0.0, expected_score=500.0)
    discard = _plan(DISCARD_CARDS, 0.0)
    policy = SimpleNamespace(EPSILON=1e-12)
    state = SimpleNamespace(jokers=[_joker("Runner")])

    selected = _green_preserving_play(
        policy,
        state,
        (play, discard),
        _decision(discard),
    )

    assert selected is None
