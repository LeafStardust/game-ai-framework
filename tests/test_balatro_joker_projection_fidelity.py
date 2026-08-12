from games.balatro.build.joker_projection_fidelity import (
    DEFERRED,
    ERROR,
    GAP,
    SUPPORTED,
    JokerProjectionFidelityAuditor,
)


def test_every_hydrated_mutable_joker_has_explicit_runtime_projection_status():
    report = JokerProjectionFidelityAuditor().audit()

    assert report.count(SUPPORTED) == 25
    assert report.count(DEFERRED) == 8
    assert report.count(GAP) == 0
    assert report.count(ERROR) == 0


def test_deferred_jokers_explain_their_remaining_projection_blocker():
    report = JokerProjectionFidelityAuditor().audit()
    entries = {entry.class_name: entry for entry in report.entries}

    expected_fragments = {
        "CanioJoker": "destroyed-card",
        "LoyaltyCardJoker": "HAND_PLAYED",
        "LuckyCatJoker": "LUCKY_TRIGGERED",
        "ObeliskJoker": "most-played-hand",
        "RedCardJoker": "accumulated hydrated Mult",
        "RideTheBusJoker": "scoring-card identity",
        "SeltzerJoker": "retrigger",
        "VampireJoker": "isolated branch card copies",
    }

    for class_name, fragment in expected_fragments.items():
        assert entries[class_name].status == DEFERRED
        assert fragment in entries[class_name].reason
