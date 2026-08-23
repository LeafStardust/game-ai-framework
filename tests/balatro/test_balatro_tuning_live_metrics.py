import json
from pathlib import Path

from games.balatro.tuning.live_metrics import episode_metrics_from_run_log


def _row(run_id, sequence, event, data):
    return {
        "schema": "balatro-run-experience-v1",
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
                    "payload": {
                        "ante_num": 5,
                        "score": 1200,
                        "blind": {"score": 1000, "type": "BOSS"},
                    },
                },
            },
        ),
        _row(
            run_id,
            4,
            "run_finished",
            {
                "won": True,
                "reason": "game_over",
                "state": {
                    "phase": "GAME_OVER",
                    "payload": {"ante_num": 8, "score": 100000, "blind": {"score": 100000}, "won": True},
                },
            },
        ),
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    metrics = episode_metrics_from_run_log(path)

    assert metrics.won is True
    assert metrics.ante_reached == 8
    assert metrics.scaling_score == 0.6
    assert metrics.survival_margin == 0.8
    assert metrics.power_engine_utilization == 1.0
    assert metrics.motif_mature_count == 1
    assert metrics.d1_mean_seconds == 2.5
    assert "burnt" in metrics.build_signature
