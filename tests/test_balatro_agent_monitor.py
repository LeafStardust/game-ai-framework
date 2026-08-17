from games.balatro.live.external.balatro_agent_monitor import build_dashboard


def test_dashboard_shows_current_run_last_decision_and_live_activity():
    status = {
        "state": "ON",
        "session_id": "session-1",
        "attempt": 3,
        "run_id": "session-1-attempt-003",
        "deck": "RED",
        "stake": "WHITE",
        "playbook": "red-white",
        "playbook_version": "0.8",
        "phase": "SHOP",
    }
    rows = [
        {
            "sequence": 11,
            "event": "decision",
            "timestamp": "2026-08-14T08:00:00+00:00",
            "data": {
                "action": {"name": "PLAY_CARDS", "indices": [0, 2]},
                "rationale": {
                    "decision_source": "D1 hand-action policy",
                    "notes": ["pace_ratio=1.20", "clear_probability=0.75"],
                },
            },
        },
        {
            "sequence": 12,
            "event": "action_result",
            "timestamp": "2026-08-14T08:00:01+00:00",
            "data": {
                "action": {"name": "PLAY_CARDS", "indices": [0, 2]},
                "success": True,
                "state": {
                    "phase": "SELECTING_HAND",
                    "sequence": 50,
                    "state_complete": True,
                    "payload": {
                        "ante_num": 2,
                        "round_num": 4,
                        "score": 220,
                        "money": 9,
                        "blind": {"score": 450},
                        "round": {"hands_left": 2, "discards_left": 1},
                    },
                },
            },
        },
    ]
    telemetry = {
        "activity": "THINKING",
        "phase": "SELECTING_HAND",
        "action": "-",
        "decision_source": "D1 hand-action policy",
        "detail": "evaluating the current settled checkpoint",
        "notes": ["searching clear paths"],
    }

    text = build_dashboard(
        status,
        supervisor_pid=1234,
        balatro_running=True,
        rows=rows,
        telemetry=telemetry,
    )

    assert "Run ongoing     : YES" in text
    assert "Agent activity   : THINKING" in text
    assert "Attempt         : 3" in text
    assert "Deck / Stake    : RED / WHITE" in text
    assert "Current phase   : SELECTING_HAND" in text
    assert "Score / Blind   : 220 / 450" in text
    assert "Activity        : THINKING" in text
    assert "evaluating the current settled checkpoint" in text
    assert "searching clear paths" in text
    assert "Action          : PLAY_CARDS indices=0,2" in text
    assert "Decision source : D1 hand-action policy" in text
    assert "pace_ratio=1.20" in text
    assert "clear_probability=0.75" in text


def test_dashboard_reports_stopped_run():
    text = build_dashboard(
        {"state": "OFF", "reason": "manual stop requested"},
        supervisor_pid=None,
        balatro_running=False,
        rows=[],
        telemetry={"activity": "OFF"},
    )

    assert "Agent activity   : OFF" in text
    assert "Supervisor      : STOPPED" in text
    assert "Balatro.exe     : NOT RUNNING" in text
    assert "Run ongoing     : NO" in text
    assert "Status reason    : manual stop requested" in text


def test_dashboard_shows_strategy_diagnostics_outside_truncated_reasoning():
    rows = [
        {
            "sequence": 11,
            "event": "decision",
            "data": {
                "action": {"name": "PLAY_CARDS", "indices": [0]},
                "rationale": {
                    "decision_source": "D1 hand-action policy",
                    "notes": [f"ordinary note {index}" for index in range(12)],
                    "postmortem": {
                        "strategy": {
                            "dominant_strategy_id": "high_card_stuntman",
                            "relevant_strategy_ids": ["pair"],
                            "active_status": "HIGHLIGHTED",
                            "strategy_pressure": 0.625,
                            "ranked": [
                                {
                                    "strategy_id": "high_card_stuntman",
                                    "name": "Stuntman / Small-Hand High Card",
                                    "score": 8.25,
                                },
                                {
                                    "strategy_id": "pair",
                                    "name": "Pair",
                                    "score": 3.5,
                                },
                            ],
                            "nodes": [
                                {
                                    "strategy_id": "high_card_stuntman",
                                    "path": ["high_card", "high_card_stuntman"],
                                }
                            ],
                        }
                    },
                },
            },
        }
    ]

    text = build_dashboard(
        {"state": "ON"},
        supervisor_pid=1234,
        balatro_running=True,
        rows=rows,
    )

    assert "CURRENT STRATEGY" in text
    assert "Strategy        : Stuntman / Small-Hand High Card" in text
    assert "Status          : HIGHLIGHTED" in text
    assert "Score           : 8.250" in text
    assert "Pressure        : 0.625" in text
    assert "Relevant        : Pair" in text
    assert "Path            : High Card -> Stuntman / Small-Hand High Card" in text


def test_dashboard_reports_when_no_strategy_has_positive_evidence():
    rows = [
        {
            "event": "decision",
            "data": {
                "rationale": {
                    "postmortem": {
                        "strategy": {
                            "dominant_strategy_id": None,
                            "relevant_strategy_ids": [],
                            "active_status": "AVAILABLE",
                            "strategy_pressure": 0.0,
                            "ranked": [],
                            "nodes": [],
                        }
                    }
                }
            },
        }
    ]

    text = build_dashboard(
        {"state": "ON"},
        supervisor_pid=1234,
        balatro_running=True,
        rows=rows,
    )

    assert "Strategy        : NONE (ordinary/meta value leads)" in text
    assert "Status          : AVAILABLE" in text
    assert "Score           : -" in text
    assert "Pressure        : 0.000" in text
    assert "Relevant        : NONE" in text
    assert "Path            : -" in text
