from types import SimpleNamespace

import games.balatro.build_health_diagnostics as diagnostics
from games.balatro.build_health import BuildHealth


def _health():
    return BuildHealth(
        total=50.0,
        survival=60.0,
        immediate=60.0,
        scaling=40.0,
        coherence=50.0,
        runway=50.0,
        critical=False,
        scaling_deficit=True,
        warnings=("fixture",),
        engines=(),
    )


def test_diagnostics_clone_strategy_tracker_for_health_and_roles(monkeypatch):
    class _Tracker:
        def __init__(self):
            self.calls = 0

    class _Health:
        def evaluate(self, state, *, strategy_tracker=None):
            del state
            strategy_tracker.calls += 1
            return _health()

    class _Roles:
        def classify(self, state, *, strategy_tracker=None):
            del state
            strategy_tracker.calls += 1
            return ()

    tracker = _Tracker()
    monkeypatch.setattr(diagnostics, "_HEALTH", _Health())
    monkeypatch.setattr(diagnostics, "_ROLES", _Roles())

    payload = diagnostics.build_health_diagnostics_payload(
        SimpleNamespace(),
        strategy_tracker=tracker,
    )

    assert payload["total"] == 50.0
    assert payload["scaling_deficit"] is True
    assert tracker.calls == 0
