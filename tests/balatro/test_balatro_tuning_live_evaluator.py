import json
from pathlib import Path
from types import SimpleNamespace

from games.balatro.bonds.calibration import BondCalibration, current_bond_calibration
from games.balatro.tuning.live_evaluator import AuthoritativeLiveBatchEvaluator


def _write_run(path: Path, run_id: str):
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
                "won": False,
                "reason": "game over (lost)",
                "state": {"phase": "GAME_OVER", "payload": {"ante_num": 4, "won": False}},
            },
        }
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_live_evaluator_holds_one_calibration_and_preserves_run_ids(tmp_path: Path):
    run_dir = tmp_path / "runs"
    run_dir.mkdir()
    session_dir = tmp_path / "sessions"
    control_dir = tmp_path / "control"
    observed = []

    class _Supervisor:
        def __init__(self, **kwargs):
            observed.append(("init", kwargs["max_attempts"]))

        def run(self):
            observed.append(("calibration", current_bond_calibration().synergy_bonus))
            run_id = "live-trial-001"
            _write_run(run_dir / f"{run_id}.jsonl", run_id)
            attempt = SimpleNamespace(run_id=run_id, outcome="LOSS", deck="RED", stake="WHITE")
            return SimpleNamespace(
                session_id="session-live",
                attempts=(attempt,),
                won=False,
                stop_reason="attempt limit reached (1); auto-off before next run",
            )

    evaluator = AuthoritativeLiveBatchEvaluator(
        attempts_per_trial=1,
        run_log_directory=run_dir,
        session_directory=session_dir,
        control_directory=control_dir,
        supervisor_factory=_Supervisor,
        reset_after_loss=False,
    )
    calibration = BondCalibration(synergy_bonus=2.25)

    result = evaluator.evaluate(calibration)

    assert result.session_id == "session-live"
    assert result.run_ids == ("live-trial-001",)
    assert result.metrics.average_ante == 4.0
    assert observed == [("init", 1), ("calibration", 2.25)]
    assert current_bond_calibration().synergy_bonus != 2.25
