from contextlib import contextmanager

from games.balatro.bonds.calibration import DEFAULT_BOND_CALIBRATION
from games.balatro.tuning import live_evaluator


def test_production_default_tuning_baseline_skips_context_override(monkeypatch):
    calls = []

    @contextmanager
    def fake_use_bond_calibration(calibration):
        calls.append(calibration)
        yield calibration

    monkeypatch.setattr(live_evaluator, "use_bond_calibration", fake_use_bond_calibration)

    with live_evaluator._calibration_context(DEFAULT_BOND_CALIBRATION) as active:
        assert active == DEFAULT_BOND_CALIBRATION

    assert calls == []


def test_candidate_tuning_calibration_keeps_context_override(monkeypatch):
    calls = []
    candidate = DEFAULT_BOND_CALIBRATION.with_overrides(
        realization_priority_weight=(
            DEFAULT_BOND_CALIBRATION.realization_priority_weight + 0.25
        )
    )

    @contextmanager
    def fake_use_bond_calibration(calibration):
        calls.append(calibration)
        yield calibration

    monkeypatch.setattr(live_evaluator, "use_bond_calibration", fake_use_bond_calibration)

    with live_evaluator._calibration_context(candidate) as active:
        assert active == candidate

    assert calls == [candidate]
