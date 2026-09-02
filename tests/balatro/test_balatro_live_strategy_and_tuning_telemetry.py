from __future__ import annotations

import json
from pathlib import Path

import pytest

from games.balatro.tuning.live_metrics_runtime import episode_metrics_from_run_log


def _row(run_id: str, sequence: int, event: str, data: dict) -> dict:
    return {
        "schema": "balatro-run-experience-v1",
        "run_id": run_id,
        "sequence": sequence,
        "event": event,
        "deck": "RED",
        "stake": "WHITE",
        "playbook": "red-white",
        "playbook_version": "1.0",
        "data": data,
    }


def test_runtime_metrics_parse_actual_live_note_schema(tmp_path: Path) -> None:
    run_id = "telemetry-contract"
    path = tmp_path / f"{run_id}.jsonl"
    rows = [
        _row(run_id, 1, "run_started", {}),
        _row(
            run_id,
            2,
            "decision",
            {
                "rationale": {
                    "decision_source": "D1 hand-action policy",
                    "notes": [
                        "d1_decision_seconds=1.382",
                        "Build Health survival=100.0 immediate=100.0 scaling=25.0",
                    ],
                    "postmortem": {
                        "bond_strategy": {
                            "power_engine": "spades",
                            "relevant_bonds": [
                                {
                                    "bond_id": "spades",
                                    "rank": "R2",
                                    "realization": "ACTIVE",
                                    "contribution": 9.0,
                                }
                            ],
                            "composition": {
                                "motifs": [{"motif_id": "example", "state": "MATURE"}]
                            },
                        }
                    },
                }
            },
        ),
        _row(
            run_id,
            3,
            "run_finished",
            {
                "won": False,
                "state": {
                    "phase": "GAME_OVER",
                    "payload": {
                        "ante_num": 4,
                        "score": 9000,
                        "blind": {"score": 10000, "type": "BOSS"},
                    },
                },
            },
        ),
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    metrics = episode_metrics_from_run_log(path)

    assert metrics.d1_mean_seconds == pytest.approx(1.382)
    assert metrics.d1_max_seconds == pytest.approx(1.382)
    assert metrics.survival_margin == pytest.approx(1.0)
    assert metrics.scaling_score == pytest.approx(0.25)
    assert metrics.power_engine_utilization == pytest.approx(1.0)
    assert metrics.motif_mature_count == 1
