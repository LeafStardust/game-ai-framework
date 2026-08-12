from games.balatro.build.joker_projection_fidelity import (
    DEFERRED,
    ERROR,
    GAP,
    SUPPORTED,
    JokerProjectionFidelityAuditor,
)


def test_every_hydrated_mutable_joker_has_exact_runtime_projection_support():
    report = JokerProjectionFidelityAuditor().audit()

    assert report.count(SUPPORTED) == 33
    assert report.count(DEFERRED) == 0
    assert report.count(GAP) == 0
    assert report.count(ERROR) == 0
