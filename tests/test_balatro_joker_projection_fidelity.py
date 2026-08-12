from games.balatro.build.joker_projection_fidelity import (
    DEFERRED,
    ERROR,
    GAP,
    SUPPORTED,
    JokerProjectionFidelityAuditor,
)


def test_every_hydrated_mutable_joker_has_explicit_runtime_projection_status():
    report = JokerProjectionFidelityAuditor().audit()

    assert report.count(SUPPORTED) == 3
    assert report.count(DEFERRED) == 30
    assert report.count(GAP) == 0
    assert report.count(ERROR) == 0


def test_event_and_stochastic_deferrals_explain_why_projection_is_not_exact_yet():
    report = JokerProjectionFidelityAuditor().audit()
    entries = {entry.class_name: entry for entry in report.entries}

    assert entries["LoyaltyCardJoker"].status == DEFERRED
    assert "HAND_PLAYED" in entries["LoyaltyCardJoker"].reason
    assert entries["LuckyCatJoker"].status == DEFERRED
    assert "LUCKY_TRIGGERED" in entries["LuckyCatJoker"].reason
