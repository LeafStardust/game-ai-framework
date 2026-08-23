import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from games.balatro.bonds.calibration import BondCalibration, current_bond_calibration
from games.balatro.tuning.live_evaluator import AuthoritativeLiveBatchEvaluator


def _write_run(path: Path, run_id: str, *, won=False, ante=4):
    rows = [
        {
            "schema": "balatro-run-experience-v1",
            "run_id": run_id,
            "deck": "RED",
            "stake": "WHITE",
            "playbook": "red-white",
            "playbook_version": "1.0",
            "sequence": 1,
            "event": "run_finished",
            "timestamp": "2026-08-23T00:00:00+00:00",
            "data": {
                "won": won,
                "reason": "game over (won)" if won else "game over (lost)",
                "state": {"phase": "GAME_OVER", "payload": {"ante_num": ante, "won": won}},
            },
        }
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _attempt(run_id, *, outcome="LOSS"):
    return SimpleNamespace(run_id=run_id, outcome=outcome, deck="RED", stake="WHITE")


def _preflight(**kwargs):
    return SimpleNamespace(deck=kwargs["expected_deck"], stake=kwargs["expected_stake"])


def _evaluator(tmp_path: Path, supervisor_factory, *, attempts=1, reset=False, preflight=_preflight):
    run_dir = tmp_path / "runs"
    run_dir.mkdir(exist_ok=True)
    return AuthoritativeLiveBatchEvaluator(
        attempts_per_trial=attempts,
        run_log_directory=run_dir,
        session_directory=tmp_path / "sessions",
        control_directory=tmp_path / "control",
        supervisor_factory=supervisor_factory,
        preflight_validator=preflight,
        reset_after_loss=reset,
    )


def test_live_evaluator_preflights_before_entering_calibration_context(tmp_path: Path):
    order = []
    baseline = current_bond_calibration()

    def preflight(**kwargs):
        order.append(("preflight", current_bond_calibration()))
        assert kwargs == {"expected_deck": "RED", "expected_stake": "WHITE"}

    class _Supervisor:
        def __init__(self, **kwargs): pass
        def run(self):
            order.append(("run", current_bond_calibration()))
            raise RuntimeError("stop after boundary assertion")

    evaluator = _evaluator(tmp_path, _Supervisor, preflight=preflight)
    with pytest.raises(RuntimeError, match="boundary assertion"):
        evaluator.evaluate(BondCalibration(synergy_bonus=2.25))
    assert order[0] == ("preflight", baseline)
    assert order[1][0] == "run"
    assert order[1][1].synergy_bonus == pytest.approx(2.25)
    assert current_bond_calibration() is baseline


def test_live_evaluator_does_not_construct_supervisor_when_preflight_fails(tmp_path: Path):
    constructed = []

    def preflight(**kwargs):
        raise RuntimeError("not fresh")

    class _Supervisor:
        def __init__(self, **kwargs):
            constructed.append(True)

    evaluator = _evaluator(tmp_path, _Supervisor, preflight=preflight)
    with pytest.raises(RuntimeError, match="not fresh"):
        evaluator.evaluate(BondCalibration())
    assert constructed == []


def test_live_evaluator_holds_one_calibration_and_preserves_run_ids(tmp_path: Path):
    observed = []
    run_dir = tmp_path / "runs"
    run_dir.mkdir()

    class _Supervisor:
        def __init__(self, **kwargs):
            observed.append(("init", kwargs["max_attempts"]))
        def run(self):
            observed.append(("calibration", current_bond_calibration().synergy_bonus))
            run_id = "live-trial-001"
            _write_run(run_dir / f"{run_id}.jsonl", run_id)
            return SimpleNamespace(session_id="session-live", attempts=(_attempt(run_id),), won=False,
                                   stop_reason="attempt limit reached (1); auto-off before next run")

    evaluator = AuthoritativeLiveBatchEvaluator(
        attempts_per_trial=1,
        run_log_directory=run_dir,
        session_directory=tmp_path / "sessions",
        control_directory=tmp_path / "control",
        supervisor_factory=_Supervisor,
        preflight_validator=_preflight,
        reset_after_loss=False,
    )
    baseline = current_bond_calibration()
    result = evaluator.evaluate(BondCalibration(synergy_bonus=2.25))

    assert result.session_id == "session-live"
    assert result.run_ids == ("live-trial-001",)
    assert result.metrics.average_ante == 4.0
    assert observed == [("init", 1), ("calibration", 2.25)]
    assert current_bond_calibration() is baseline


def test_live_evaluator_restores_calibration_when_supervisor_raises(tmp_path: Path):
    baseline = current_bond_calibration()

    class _Supervisor:
        def __init__(self, **kwargs): pass
        def run(self):
            assert current_bond_calibration().synergy_bonus == pytest.approx(2.4)
            raise RuntimeError("boom")

    evaluator = _evaluator(tmp_path, _Supervisor)
    with pytest.raises(RuntimeError, match="boom"):
        evaluator.evaluate(BondCalibration(synergy_bonus=2.4))
    assert current_bond_calibration() is baseline


def test_live_evaluator_rejects_session_without_attempts(tmp_path: Path):
    class _Supervisor:
        def __init__(self, **kwargs): pass
        def run(self):
            return SimpleNamespace(session_id="empty", attempts=(), won=False, stop_reason="blocked")

    evaluator = _evaluator(tmp_path, _Supervisor)
    with pytest.raises(RuntimeError, match="without an attempt"):
        evaluator.evaluate(BondCalibration())


def test_live_evaluator_rejects_supervisor_exceeding_attempt_cap(tmp_path: Path):
    run_dir = tmp_path / "runs"
    run_dir.mkdir()

    class _Supervisor:
        def __init__(self, **kwargs): pass
        def run(self):
            for run_id in ("one", "two"):
                _write_run(run_dir / f"{run_id}.jsonl", run_id)
            return SimpleNamespace(session_id="too-many", attempts=(_attempt("one"), _attempt("two")),
                                   won=False, stop_reason="bad supervisor")

    evaluator = AuthoritativeLiveBatchEvaluator(
        attempts_per_trial=1, run_log_directory=run_dir,
        session_directory=tmp_path / "sessions", control_directory=tmp_path / "control",
        supervisor_factory=_Supervisor, preflight_validator=_preflight, reset_after_loss=False,
    )
    with pytest.raises(RuntimeError, match="exceeded its attempt cap"):
        evaluator.evaluate(BondCalibration())


def test_live_evaluator_fails_when_expected_run_log_is_missing(tmp_path: Path):
    class _Supervisor:
        def __init__(self, **kwargs): pass
        def run(self):
            return SimpleNamespace(session_id="missing-log", attempts=(_attempt("missing"),),
                                   won=False, stop_reason="attempt limit reached")

    evaluator = _evaluator(tmp_path, _Supervisor)
    with pytest.raises(FileNotFoundError):
        evaluator.evaluate(BondCalibration())


def test_loss_reset_rejects_non_loss_terminal_boundary_without_touching_live_api(tmp_path: Path):
    evaluator = _evaluator(tmp_path, lambda **kwargs: None, reset=True)
    result = SimpleNamespace(won=False, attempts=(_attempt("blocked", outcome="BLOCKED"),))
    with pytest.raises(RuntimeError, match="restartable LOSS boundary"):
        evaluator._reset_terminal_loss(result)


def test_loss_reset_rejects_deck_stake_drift_before_live_api(tmp_path: Path):
    evaluator = _evaluator(tmp_path, lambda **kwargs: None, reset=True)
    bad = SimpleNamespace(run_id="bad", outcome="LOSS", deck="BLUE", stake="WHITE")
    with pytest.raises(RuntimeError, match="identity drifted"):
        evaluator._reset_terminal_loss(SimpleNamespace(won=False, attempts=(bad,)))


def test_winning_result_never_enters_loss_reset_path(tmp_path: Path):
    evaluator = _evaluator(tmp_path, lambda **kwargs: None, reset=True)
    # This must return before importing/initializing any live observer or restart machinery.
    evaluator._reset_terminal_loss(SimpleNamespace(won=True, attempts=(_attempt("winner", outcome="WIN"),)))


def test_constructor_rejects_nonpositive_attempt_count(tmp_path: Path):
    with pytest.raises(ValueError, match="attempts_per_trial"):
        AuthoritativeLiveBatchEvaluator(attempts_per_trial=0)


def test_constructor_rejects_blank_identity():
    with pytest.raises(ValueError, match="deck/stake"):
        AuthoritativeLiveBatchEvaluator(deck="", stake="WHITE")
