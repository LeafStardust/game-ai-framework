from types import SimpleNamespace

import games.balatro.latest_batch_build_quality_policy as policy


def _health(*, immediate=60.0, scaling=40.0, total=55.0):
    return SimpleNamespace(
        immediate=float(immediate),
        scaling=float(scaling),
        total=float(total),
        survival=60.0,
        critical=False,
        scaling_deficit=True,
    )


def test_observed_hand_specialization_requires_repeated_dominance():
    state = SimpleNamespace(
        hand_play_counts={
            "Two Pair": 15,
            "Pair": 4,
            "Flush": 3,
        }
    )
    specialized, observed, runner_up = policy.observed_hand_specialization(
        state,
        "Two Pair",
    )

    assert specialized is True
    assert observed == 15
    assert runner_up == 4


def test_observed_hand_specialization_does_not_promote_mixed_history():
    state = SimpleNamespace(
        hand_play_counts={
            "Pair": 8,
            "Two Pair": 7,
            "Flush": 5,
        }
    )
    specialized, observed, runner_up = policy.observed_hand_specialization(
        state,
        "Pair",
    )

    assert specialized is False
    assert observed == 8
    assert runner_up == 7


def test_positive_replacement_can_displace_non_scoring_slot_when_build_is_weak(monkeypatch):
    incumbent = SimpleNamespace(name="Credit Card")
    candidate = SimpleNamespace(name="Scaling Joker")
    state = SimpleNamespace(
        jokers=[incumbent] * 5,
        joker_slots=5,
        ante=5,
    )
    option = SimpleNamespace(
        eligible=True,
        build_delta=0.10,
        replace_index=0,
        incumbent_value=SimpleNamespace(direct_scoring_gain=0.0),
        candidate_value=SimpleNamespace(direct_scoring_gain=5.0),
    )

    monkeypatch.setattr(
        policy._HEALTH,
        "evaluate",
        lambda simulated: _health(immediate=66.0, scaling=46.0, total=61.0),
    )
    result = policy._replacement_qualifies(
        state,
        candidate,
        option,
        _health(),
    )

    assert result is not None
    assert result[0] is option


def test_replacement_relaxation_never_accepts_nonpositive_whole_build_delta(monkeypatch):
    incumbent = SimpleNamespace(name="Credit Card")
    candidate = SimpleNamespace(name="Candidate")
    state = SimpleNamespace(jokers=[incumbent] * 5, joker_slots=5, ante=5)
    option = SimpleNamespace(
        eligible=True,
        build_delta=0.0,
        replace_index=0,
        incumbent_value=SimpleNamespace(direct_scoring_gain=0.0),
        candidate_value=SimpleNamespace(direct_scoring_gain=100.0),
    )

    monkeypatch.setattr(
        policy._HEALTH,
        "evaluate",
        lambda simulated: _health(immediate=100.0, scaling=100.0, total=100.0),
    )
    result = policy._replacement_qualifies(
        state,
        candidate,
        option,
        _health(),
    )

    assert result is None


def test_replacement_relaxation_preserves_prior_eligibility_blocks():
    state = SimpleNamespace(
        jokers=[SimpleNamespace(name="Protected")] * 5,
        joker_slots=5,
        ante=5,
    )
    option = SimpleNamespace(
        eligible=False,
        build_delta=99.0,
        replace_index=0,
        incumbent_value=SimpleNamespace(direct_scoring_gain=0.0),
        candidate_value=SimpleNamespace(direct_scoring_gain=100.0),
    )

    assert policy._replacement_qualifies(
        state,
        SimpleNamespace(name="Candidate"),
        option,
        _health(),
    ) is None
