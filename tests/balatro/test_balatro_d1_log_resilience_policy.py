from games.balatro.d1_log_resilience_policy import (
    _best_completed_clear_attempt,
    _best_completed_scoring_attempt,
)
from games.balatro.live.hand_action_policy import HandActionSearchAttempt


def _attempt(
    *,
    horizon,
    probability,
    score,
    action="PLAY_CARDS",
    exceeded=False,
    confirmation=False,
):
    return HandActionSearchAttempt(
        horizon=horizon,
        samples=8,
        play_width=6,
        discard_width=4,
        max_nodes=1000,
        nodes_evaluated=10,
        budget_exceeded=exceeded,
        confirmation=confirmation,
        best_action=action if score is not None else None,
        best_clear_probability=probability,
        best_expected_score=score,
        best_exact=False,
    )


def test_completed_clear_survives_later_confirmation_timeout():
    attempts = (
        _attempt(horizon=2, probability=0.375, score=295.125),
        _attempt(horizon=5, probability=1.0, score=383.5),
        _attempt(
            horizon=5,
            probability=None,
            score=None,
            exceeded=True,
            confirmation=True,
        ),
    )

    preserved = _best_completed_clear_attempt(attempts, 0.75)

    assert preserved is attempts[1]
    assert preserved.best_clear_probability == 1.0
    assert preserved.best_expected_score == 383.5


def test_budget_exceeded_attempt_never_replaces_completed_evidence():
    attempts = (
        _attempt(horizon=3, probability=0.80, score=500.0),
        _attempt(horizon=5, probability=1.0, score=900.0, exceeded=True),
    )

    preserved = _best_completed_clear_attempt(attempts, 0.75)

    assert preserved is attempts[0]


def test_completed_discard_recommendation_survives_later_timeout():
    attempts = (
        _attempt(
            horizon=2,
            probability=0.136364,
            score=116.182,
            action="DISCARD_CARDS",
        ),
        _attempt(
            horizon=4,
            probability=None,
            score=None,
            exceeded=True,
        ),
    )

    preserved = _best_completed_scoring_attempt(attempts)

    assert preserved is attempts[0]
    assert preserved.best_action == "DISCARD_CARDS"
    assert preserved.best_expected_score == 116.182


def test_deeper_completed_discard_beats_shallower_play_for_scoring_evidence():
    attempts = (
        _attempt(horizon=2, probability=0.2, score=150.0, action="PLAY_CARDS"),
        _attempt(horizon=4, probability=0.3, score=240.0, action="DISCARD_CARDS"),
    )

    preserved = _best_completed_scoring_attempt(attempts)

    assert preserved is attempts[1]
    assert preserved.best_action == "DISCARD_CARDS"
