from games.balatro.live.external.balatro_agent_monitor import build_dashboard


def test_dashboard_shows_current_run_and_last_decision():
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

    text = build_dashboard(
        status,
        supervisor_pid=1234,
        balatro_running=True,
        rows=rows,
    )

    assert "Run ongoing     : YES" in text
    assert "Attempt         : 3" in text
    assert "Deck / Stake    : RED / WHITE" in text
    assert "Current phase   : SELECTING_HAND" in text
    assert "Score / Blind   : 220 / 450" in text
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
    )

    assert "Supervisor      : STOPPED" in text
    assert "Balatro.exe     : NOT RUNNING" in text
    assert "Run ongoing     : NO" in text
    assert "Status reason    : manual stop requested" in text
