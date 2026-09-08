import json
from pathlib import Path

import pytest

from games.balatro.tuning.live_metrics import episode_metrics_from_run_log


def _row(run_id, sequence, event, data, *, schema="balatro-run-experience-v1"):
    return {
        "schema": schema,
        "run_id": run_id,
        "deck": "RED",
        "stake": "WHITE",
        "playbook": "red-white",
        "playbook_version": "1.0",
        "sequence": sequence,
        "event": event,
        "timestamp": "2026-08-23T00:00:00+00:00",
        "data": data,
    }


def _write(path: Path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _finished(run_id, sequence, *, won=False, ante=4, score=0, requirement=0):
    return _row(
        run_id,
        sequence,
        "run_finished",
        {
            "won": won,
            "reason": "game over (won)" if won else "game over (lost)",
            "state": {
                "phase": "GAME_OVER",
                "payload": {
                    "ante_num": ante,
                    "score": score,
                    "blind": {"score": requirement},
                    "won": won,
                },
            },
        },
    )


def test_live_metric_parser_extracts_terminal_and_bond_diagnostics(tmp_path: Path):
    run_id = "trial-run"
    path = tmp_path / f"{run_id}.jsonl"
    rows = [
        _row(run_id, 1, "run_started", {"state": {"phase": "BLIND_SELECT", "payload": {"ante_num": 1}}}),
        _row(
            run_id,
            2,
            "decision",
            {
                "action": {"name": "PLAY_CARDS"},
                "rationale": {
                    "postmortem": {
                        "d1_decision_seconds": 2.5,
                        "build_health": {"scaling": 60, "survival": 80},
                        "bond_strategy": {
                            "power_engine": "burnt",
                            "power_engine_realization": "ACTIVE",
                            "relevant_bonds": [{"bond_id": "burnt"}, {"bond_id": "high_card"}],
                            "motifs": [{"motif_id": "x", "state": "MATURE"}],
                        },
                    }
                },
            },
        ),
        _row(
            run_id,
            3,
            "action_result",
            {
                "action": {"name": "PLAY_CARDS"},
                "success": True,
                "state": {
                    "phase": "ROUND_EVAL",
                    "payload": {"ante_num": 5, "score": 1200, "blind": {"score": 1000, "type": "BOSS"}},
                },
            },
        ),
        _finished(run_id, 4, won=True, ante=8, score=100000, requirement=100000),
    ]
    _write(path, rows)

    metrics = episode_metrics_from_run_log(path)

    assert metrics.won is True
    assert metrics.ante_reached == 8
    assert metrics.scaling_score == pytest.approx(0.6)
    assert metrics.survival_margin == pytest.approx(0.8)
    assert metrics.power_engine_utilization == pytest.approx(1.0)
    assert metrics.motif_mature_count == 1
    assert metrics.d1_mean_seconds == pytest.approx(2.5)
    assert metrics.d1_max_seconds == pytest.approx(2.5)
    assert metrics.boss_clear_rate == pytest.approx(1.0)
    assert "burnt" in metrics.build_signature


def test_live_metric_parser_aggregates_d1_timing_and_latest_build_signature(tmp_path: Path):
    run_id = "timing-run"
    path = tmp_path / f"{run_id}.jsonl"
    rows = [
        _row(run_id, 1, "run_started", {"state": {"phase": "BLIND_SELECT", "payload": {"ante_num": 1}}}),
        _row(run_id, 2, "decision", {"rationale": {"postmortem": {"d1_decision_seconds": 2.0, "bond_strategy": {"power_engine": "burnt", "power_engine_realization": "PARTIAL", "relevant_bonds": [{"bond_id": "burnt"}]}}}}),
        _row(run_id, 3, "decision", {"rationale": {"postmortem": {"d1_decision_seconds": 6.0, "bond_strategy": {"power_engine": "pair", "power_engine_realization": "MATURE", "relevant_bonds": [{"bond_id": "pair"}, {"bond_id": "held_cards"}]}}}}),
        _finished(run_id, 4, ante=5, score=8000, requirement=10000),
    ]
    _write(path, rows)

    metrics = episode_metrics_from_run_log(path)

    assert metrics.d1_mean_seconds == pytest.approx(4.0)
    assert metrics.d1_max_seconds == pytest.approx(6.0)
    assert metrics.power_engine_utilization == pytest.approx(0.75)
    assert metrics.build_signature == "pair|held_cards|pair"
    assert metrics.blind_clear_margin == pytest.approx(-0.2)


def test_live_metric_parser_does_not_invent_missing_optional_telemetry(tmp_path: Path):
    run_id = "minimal-run"
    path = tmp_path / f"{run_id}.jsonl"
    _write(path, [_finished(run_id, 1, ante=3)])

    metrics = episode_metrics_from_run_log(path)

    assert metrics.won is False
    assert metrics.ante_reached == 3
    assert metrics.scaling_score == 0.0
    assert metrics.survival_margin == 0.0
    assert metrics.power_engine_utilization == 0.0
    assert metrics.d1_mean_seconds == 0.0
    assert metrics.d1_max_seconds == 0.0
    assert metrics.build_signature == ""


@pytest.mark.parametrize(
    "rows,error_text",
    [
        ([{"schema": "wrong", "run_id": "bad", "sequence": 1, "event": "run_finished", "data": {}}], "schema"),
        ([_finished("other", 1)], "run id mismatch"),
    ],
)
def test_live_metric_parser_rejects_identity_or_schema_corruption(tmp_path: Path, rows, error_text):
    path = tmp_path / "bad.jsonl"
    _write(path, rows)
    with pytest.raises(ValueError, match=error_text):
        episode_metrics_from_run_log(path)


def test_live_metric_parser_rejects_non_contiguous_sequence(tmp_path: Path):
    run_id = "gap"
    path = tmp_path / f"{run_id}.jsonl"
    _write(path, [_row(run_id, 1, "run_started", {}), _finished(run_id, 3)])
    with pytest.raises(ValueError, match="sequence"):
        episode_metrics_from_run_log(path)


def test_live_metric_parser_rejects_unfinished_run(tmp_path: Path):
    run_id = "unfinished"
    path = tmp_path / f"{run_id}.jsonl"
    _write(path, [_row(run_id, 1, "run_started", {"state": {"phase": "BLIND_SELECT", "payload": {}}})])
    with pytest.raises(ValueError, match="run_finished"):
        episode_metrics_from_run_log(path)


def test_live_metric_parser_rejects_invalid_json(tmp_path: Path):
    path = tmp_path / "broken.jsonl"
    path.write_text("{not-json}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        episode_metrics_from_run_log(path)
