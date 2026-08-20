from games.balatro.live.runtime import balatro_agent_monitor_targets as monitor


def _rows():
    return [
        {
            "event": "observation",
            "data": {
                "state": {
                    "phase": "SELECTING_HAND",
                    "payload": {
                        "jokers": {
                            "cards": [
                                {"label": "Hack"},
                                {"label": "Fibonacci"},
                            ]
                        }
                    },
                }
            },
        },
        {
            "event": "decision",
            "data": {
                "action": {"name": "PLAY_CARDS"},
                "rationale": {
                    "decision_source": "D1 hand-action policy",
                    "postmortem": {
                        "strategy": {
                            "dominant_strategy_id": "low_rank",
                            "active_status": "COMMITTED",
                            "strategy_pressure": 1.0,
                            "relevant_strategy_ids": [],
                            "ranked": [
                                {
                                    "strategy_id": "low_rank",
                                    "name": "Low-Rank Scoring",
                                    "score": 11.0,
                                    "rationale": [
                                        "owned gold Joker HackJoker: +8.000",
                                        "owned gold Joker FibonacciJoker: +8.000",
                                        "preferred rank concentration evidence=0.600",
                                        "environment base=+0.000; effectiveness=1.000; raw=16.600; adjusted=16.600",
                                    ],
                                }
                            ],
                            "nodes": [
                                {
                                    "strategy_id": "low_rank",
                                    "path": ["low_rank"],
                                }
                            ],
                        }
                    },
                },
            },
        },
    ]


def test_strategy_has_surfaces_score_evidence_from_postmortem() -> None:
    evidence = monitor._strategy_has(_rows())

    assert "owned gold Joker HackJoker: +8.000" in evidence
    assert "owned gold Joker FibonacciJoker: +8.000" in evidence
    assert "preferred rank concentration evidence=0.600" in evidence


def test_enriched_dashboard_places_has_between_path_and_seeking() -> None:
    rendered = monitor.build_dashboard(
        {"state": "ON"},
        supervisor_pid=123,
        balatro_running=True,
        rows=_rows(),
        telemetry={},
    )
    lines = rendered.splitlines()

    path_index = next(i for i, line in enumerate(lines) if line.startswith("Path            : "))
    has_index = next(i for i, line in enumerate(lines) if line.startswith("Has             : "))
    seeking_index = next(i for i, line in enumerate(lines) if line.startswith("Seeking         : "))

    assert has_index == path_index + 1
    assert seeking_index == has_index + 1
    assert "HackJoker: +8.000" in lines[has_index]