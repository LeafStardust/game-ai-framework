from games.balatro.live.runtime.balatro_agent_monitor import build_dashboard


def _rows(postmortem):
    return [
        {
            "event": "decision",
            "data": {
                "action": {"name": "PLAY_CARDS", "indices": [1]},
                "rationale": {"decision_source": "D1", "notes": [], "postmortem": postmortem},
            },
        }
    ]


def _status():
    return {"state": "ON", "deck": "RED", "stake": "WHITE", "playbook": "red-white", "playbook_version": "1.0"}


def test_monitor_renders_all_build_health_dimensions_and_flags():
    postmortem = {
        "layer": "D1",
        "build_health": {
            "total": 63.5,
            "survival": 82.0,
            "immediate": 71.0,
            "scaling": 34.0,
            "coherence": 69.0,
            "runway": 55.0,
            "critical": False,
            "scaling_deficit": True,
            "warnings": ["scaling deficit: projected growth is behind schedule"],
            "engines": [
                {"engine_id": "hologram", "state": "OWNED_INACTIVE"},
                {"engine_id": "cash_scoring", "state": "ACTIVATED_HEALTHY"},
            ],
        },
        "component_roles": [
            {"name": "Hologram", "role": "ENGINE"},
            {"name": "Joker", "role": "FILLER"},
        ],
    }
    text = build_dashboard(_status(), supervisor_pid=1, balatro_running=True, rows=_rows(postmortem))
    assert text.count("BUILD HEALTH / REALIZED STRENGTH") == 1
    assert "Health total    : 63.5%" in text
    assert "Survival        : 82.0%" in text
    assert "Immediate       : 71.0%" in text
    assert "Scaling         : 34.0%" in text
    assert "Coherence       : 69.0%" in text
    assert "Runway          : 55.0%" in text
    assert "Scaling deficit : True" in text
    assert "hologram=OWNED_INACTIVE" in text
    assert "cash_scoring=ACTIVATED_HEALTHY" in text
    assert "Hologram=ENGINE" in text
    assert "Joker=FILLER" in text
    assert "projected growth is behind schedule" in text


def test_monitor_accepts_nested_structured_build_health_payload():
    postmortem = {
        "layer": "D13",
        "diagnostics": {
            "realized_strength": {
                "build_health": {
                    "total": 88.0,
                    "survival": 95.0,
                    "immediate": 90.0,
                    "scaling": 80.0,
                    "coherence": 85.0,
                    "runway": 90.0,
                    "critical": False,
                    "scaling_deficit": False,
                    "warnings": [],
                },
                "realized_engines": [{"engine_id": "runner", "state": "MATURE"}],
                "joker_roles": {"CORE": ["Runner"], "SUPPORT": ["Shortcut"]},
            }
        },
    }
    text = build_dashboard(_status(), supervisor_pid=1, balatro_running=True, rows=_rows(postmortem))
    assert "Health total    : 88.0%" in text
    assert "runner=MATURE" in text
    assert "CORE=[Runner]" in text
    assert "SUPPORT=[Shortcut]" in text
    assert "Warnings         : NONE" in text


def test_monitor_degrades_cleanly_when_health_diagnostics_are_absent():
    text = build_dashboard(_status(), supervisor_pid=1, balatro_running=True, rows=_rows({"layer": "D1"}))
    assert "STRATEGY / COMPOSITION" in text
    assert "Power engine    : -" in text
    assert "Relevant Bonds  : -" in text
    assert "BUILD HEALTH / REALIZED STRENGTH" in text
    assert "Health total    : -" in text
    assert "Engines         : NONE" in text
    assert "Component roles : NONE" in text
    assert "Warnings         : -" in text
