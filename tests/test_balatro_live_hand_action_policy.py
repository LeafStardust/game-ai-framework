from types import SimpleNamespace

import pytest

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.live.blind_clear_planner import LiveBlindPlan, LiveBlindPlanValue
from games.balatro.live.hand_action_policy import (
    CLEAR_PATH,
    PACE_PLAY,
    PACE_RECOVERY,
    HandActionThresholds,
    LiveHandActionPolicy,
)


class _FakeEvaluator:
    def project_play(self, state, action):
        return SimpleNamespace(expected_hand_score=float(action.target["immediate_score"]))

    def evaluate(self, state, action):
        return float(action.target.get("fallback_value", 0.0))


def _state(*, score=0, target=300, hands=3, discards=2):
    return SimpleNamespace(
        phase="SELECTING_HAND",
        score=score,
        blind=SimpleNamespace(requirement=target),
        hands_remaining=hands,
        discards_remaining=discards,
    )


def _plan(
    action_name,
    *,
    clear,
    progress,
    immediate_score=0.0,
    fallback_value=0.0,
    hands=2.0,
    discards=1.0,
    score=100.0,
    exact=True,
    marker=None,
):
    action = BalatroAction(
        action_name,
        cards=[marker] if marker is not None else [],
        target={
            "immediate_score": immediate_score,
            "fallback_value": fallback_value,
        },
    )
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


def _policy(**thresholds):
    return LiveHandActionPolicy(
        HandActionThresholds(**thresholds),
        evaluator=_FakeEvaluator(),
    )


def test_threshold_mapping_rejects_unknown_d1_field():
    with pytest.raises(ValueError, match="unknown D1 hand-action threshold"):
        HandActionThresholds.from_mapping({"shop_reserve_floor": 4})


def test_clear_path_takes_priority_over_pace_fallback():
    play = _plan(
        PLAY_CARDS,
        clear=0.80,
        progress=0.90,
        immediate_score=40.0,
        fallback_value=10.0,
        marker="path",
    )
    discard = _plan(
        DISCARD_CARDS,
        clear=0.20,
        progress=0.50,
        fallback_value=999.0,
        marker="tempting-discard",
    )

    decision = _policy().decide(_state(target=300, hands=3), [discard, play])

    assert decision.mode == CLEAR_PATH
    assert decision.action.cards == ["path"]
    assert decision.clear_path_candidates == 1
    assert decision.pace_target == pytest.approx(100.0)
    assert "re-observe and replan" in decision.rationale[1]


def test_clear_path_may_start_with_discard():
    play = _plan(
        PLAY_CARDS,
        clear=0.40,
        progress=0.60,
        immediate_score=120.0,
        marker="play",
    )
    discard = _plan(
        DISCARD_CARDS,
        clear=0.85,
        progress=0.90,
        fallback_value=0.0,
        marker="setup",
    )

    decision = _policy().decide(_state(), [play, discard])

    assert decision.mode == CLEAR_PATH
    assert decision.action.name == DISCARD_CARDS
    assert decision.action.cards == ["setup"]


def test_pace_target_is_remaining_blind_score_divided_by_hands():
    play = _plan(
        PLAY_CARDS,
        clear=0.0,
        progress=0.2,
        immediate_score=100.0,
    )

    decision = _policy().decide(
        _state(score=180, target=600, hands=3, discards=0),
        [play],
    )

    assert decision.pace_target == pytest.approx(140.0)


def test_no_clear_path_plays_when_current_hand_meets_pace():
    under = _plan(
        PLAY_CARDS,
        clear=0.20,
        progress=0.40,
        immediate_score=90.0,
        marker="under",
    )
    meets = _plan(
        PLAY_CARDS,
        clear=0.30,
        progress=0.60,
        immediate_score=110.0,
        marker="meets",
    )
    discard = _plan(
        DISCARD_CARDS,
        clear=0.10,
        progress=0.50,
        fallback_value=999.0,
        marker="discard",
    )

    decision = _policy().decide(
        _state(target=300, hands=3),
        [under, discard, meets],
    )

    assert decision.mode == PACE_PLAY
    assert decision.action.cards == ["meets"]
    assert decision.selected_pace_ratio == pytest.approx(1.10)


def test_no_pace_play_uses_pace_aware_recovery_and_can_discard():
    play = _plan(
        PLAY_CARDS,
        clear=0.10,
        progress=0.30,
        immediate_score=60.0,
        fallback_value=20.0,
        marker="play",
    )
    discard = _plan(
        DISCARD_CARDS,
        clear=0.05,
        progress=0.40,
        fallback_value=80.0,
        marker="discard",
    )

    decision = _policy().decide(
        _state(target=300, hands=3),
        [play, discard],
    )

    assert decision.mode == PACE_RECOVERY
    assert decision.action.name == DISCARD_CARDS
    assert decision.action.cards == ["discard"]
    assert "setup discard" in decision.rationale[2]


def test_last_discard_penalty_can_prevent_marginal_recovery_discard():
    policy = _policy(
        low_discard_reserve=1,
        low_discard_fallback_penalty=10.0,
    )
    play = _plan(
        PLAY_CARDS,
        clear=0.0,
        progress=0.20,
        immediate_score=50.0,
        fallback_value=50.0,
        marker="play",
    )
    discard = _plan(
        DISCARD_CARDS,
        clear=0.0,
        progress=0.25,
        fallback_value=55.0,
        marker="discard",
    )

    decision = policy.decide(
        _state(target=300, hands=3, discards=1),
        [play, discard],
    )

    assert decision.mode == PACE_RECOVERY
    assert decision.action.name == PLAY_CARDS


def test_last_hand_bonus_can_favor_discard_to_preserve_the_hand():
    policy = _policy(
        low_discard_reserve=0,
        low_hand_reserve=1,
        low_hand_discard_fallback_bonus=10.0,
    )
    play = _plan(
        PLAY_CARDS,
        clear=0.0,
        progress=0.20,
        immediate_score=50.0,
        fallback_value=50.0,
        marker="play",
    )
    discard = _plan(
        DISCARD_CARDS,
        clear=0.0,
        progress=0.25,
        fallback_value=45.0,
        marker="discard",
    )

    decision = policy.decide(
        _state(target=300, hands=1, discards=2),
        [play, discard],
    )

    assert decision.mode == PACE_RECOVERY
    assert decision.action.name == DISCARD_CARDS


def test_clear_path_floor_is_a_real_boundary():
    below = _plan(
        PLAY_CARDS,
        clear=0.749,
        progress=0.80,
        immediate_score=100.0,
        marker="below",
    )
    at_floor = _plan(
        PLAY_CARDS,
        clear=0.75,
        progress=0.75,
        immediate_score=10.0,
        marker="at-floor",
    )

    decision = _policy().decide(_state(), [below, at_floor])

    assert decision.mode == CLEAR_PATH
    assert decision.action.cards == ["at-floor"]


def test_setup_discard_consensus_is_reported_in_recovery_rationale():
    play = _plan(
        PLAY_CARDS,
        clear=0.0,
        progress=0.20,
        immediate_score=50.0,
        fallback_value=10.0,
    )
    discard = _plan(
        DISCARD_CARDS,
        clear=0.0,
        progress=0.30,
        fallback_value=50.0,
    )

    decision = _policy().decide(
        _state(),
        [play, discard],
        setup_discard_consensus=True,
    )

    assert decision.mode == PACE_RECOVERY
    assert decision.setup_discard_consensus is True
    assert any("deep adaptive searches" in reason for reason in decision.rationale)
