from types import SimpleNamespace

import pytest

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.hand_action_policy import (
    HandActionThresholds,
    LiveHandActionThresholdPolicy,
)


def _state(*, hands=3, discards=2):
    return SimpleNamespace(
        phase="SELECTING_HAND",
        hands_remaining=hands,
        discards_remaining=discards,
    )


def _plan(
    action_name,
    *,
    clear,
    progress,
    hands=2.0,
    discards=1.0,
    score=100.0,
    exact=True,
    marker=None,
):
    action = BalatroAction(action_name, cards=[marker] if marker is not None else [])
    return LiveBlindPlan(
        action=action,
        value=LiveBlindPlanValue(
            clear_probability=clear,
            expected_progress=progress,
            expected_score=score,
            expected_hands_remaining=hands,
            expected_discards_remaining=discards,
        ),
        horizon=2,
        exact=exact,
        candidate_count=2,
    )


def test_threshold_mapping_rejects_unknown_D1_field():
    with pytest.raises(ValueError, match="unknown D1 hand-action threshold"):
        HandActionThresholds.from_mapping({"shop_reserve_floor": 4})


def test_certain_play_is_never_replaced_by_discard():
    play = _plan(PLAY_CARDS, clear=1.0, progress=1.0)
    discard = _plan(DISCARD_CARDS, clear=1.0, progress=1.0, hands=3.0)

    decision = LiveHandActionThresholdPolicy().decide(_state(), [discard, play])

    assert decision.action.name == PLAY_CARDS
    assert "certain blind clear" in decision.rationale[0]


def test_discard_requires_clear_probability_advantage():
    play = _plan(PLAY_CARDS, clear=0.40, progress=0.55)
    discard = _plan(DISCARD_CARDS, clear=0.46, progress=0.56)

    decision = LiveHandActionThresholdPolicy().decide(_state(), [play, discard])

    assert decision.action.name == DISCARD_CARDS
    assert decision.required_discard_clear_advantage == pytest.approx(0.05)
    assert decision.clear_probability_delta == pytest.approx(0.06)


def test_last_discard_raises_required_clear_advantage():
    play = _plan(PLAY_CARDS, clear=0.40, progress=0.55)
    discard = _plan(DISCARD_CARDS, clear=0.47, progress=0.56)

    decision = LiveHandActionThresholdPolicy().decide(
        _state(discards=1),
        [play, discard],
    )

    assert decision.required_discard_clear_advantage == pytest.approx(0.10)
    assert decision.action.name == PLAY_CARDS
    assert any("low discard reserve" in reason for reason in decision.rationale)


def test_last_hand_lowers_required_discard_advantage():
    thresholds = HandActionThresholds(
        discard_clear_probability_advantage=0.05,
        low_hand_reserve=1,
        low_hand_clear_advantage_discount=0.03,
        low_discard_reserve=0,
    )
    play = _plan(PLAY_CARDS, clear=0.40, progress=0.55)
    discard = _plan(DISCARD_CARDS, clear=0.43, progress=0.56)

    decision = LiveHandActionThresholdPolicy(thresholds).decide(
        _state(hands=1, discards=2),
        [play, discard],
    )

    assert decision.required_discard_clear_advantage == pytest.approx(0.02)
    assert decision.action.name == DISCARD_CARDS


def test_progress_gate_can_choose_discard_only_when_play_is_below_floor():
    policy = LiveHandActionThresholdPolicy()
    discard = _plan(DISCARD_CARDS, clear=0.40, progress=0.70)

    below_floor = _plan(PLAY_CARDS, clear=0.40, progress=0.55)
    decision = policy.decide(_state(), [below_floor, discard])
    assert decision.action.name == DISCARD_CARDS
    assert decision.progress_delta == pytest.approx(0.15)

    above_floor = _plan(PLAY_CARDS, clear=0.80, progress=0.55)
    discard_high_progress = _plan(DISCARD_CARDS, clear=0.80, progress=0.90)
    decision = policy.decide(_state(), [above_floor, discard_high_progress])
    assert decision.action.name == PLAY_CARDS
    assert any("meets the D1 clear-probability floor" in reason for reason in decision.rationale)


def test_best_subset_is_selected_within_each_action_type():
    play_a = _plan(PLAY_CARDS, clear=0.50, progress=0.60, marker="A")
    play_b = _plan(PLAY_CARDS, clear=0.60, progress=0.65, marker="B")
    discard = _plan(DISCARD_CARDS, clear=0.40, progress=0.70, marker="D")

    decision = LiveHandActionThresholdPolicy().decide(
        _state(),
        [play_a, discard, play_b],
    )

    assert decision.action.name == PLAY_CARDS
    assert decision.action.cards == ["B"]
    assert decision.best_play.action.cards == ["B"]


def test_no_discard_candidate_falls_back_to_best_play():
    play = _plan(PLAY_CARDS, clear=0.20, progress=0.30, marker="only")

    decision = LiveHandActionThresholdPolicy().decide(
        _state(discards=0),
        [play],
    )

    assert decision.action.name == PLAY_CARDS
    assert decision.confidence == 1.0
