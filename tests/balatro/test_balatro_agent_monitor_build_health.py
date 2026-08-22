from games.balatro.live.runtime import balatro_agent_monitor as monitor


def _rows(build_health):
    return [
        {
            "event": "decision",
            "data": {
                "rationale": {
                    "postmortem": {
                        "build_health": build_health,
                    }
                }
            },
        }
    ]


def test_dashboard_renders_build_health_after_bond_composition_section():
    rows = _rows(
        {
            "total": 58.0,
            "survival": 82.0,
            "immediate": 74.0,
            "scaling": 31.0,
            "coherence": 67.0,
            "runway": 40.0,
            "critical": False,
            "scaling_deficit": True,
            "warnings": ["Ante 5 scaling deficit"],
            "engines": [{"engine_id": "hologram", "state": "OWNED_INACTIVE"}],
        }
    )

    rendered = monitor.build_dashboard(
        {"state": "ON"},
        supervisor_pid=None,
        balatro_running=True,
        rows=rows,
        telemetry=None,
    )

    assert "STRATEGY / COMPOSITION" in rendered
    assert "Power engine    : -" in rendered
    assert "Relevant Bonds  : -" in rendered
    assert "BUILD HEALTH / REALIZED STRENGTH" in rendered
    assert "Health total    : 58.0%" in rendered
    assert "Scaling         : 31.0%" in rendered
    assert "Scaling deficit : True" in rendered
    assert "hologram=OWNED_INACTIVE" in rendered
    assert "Ante 5 scaling deficit" in rendered
    assert rendered.index("STRATEGY / COMPOSITION") < rendered.index("BUILD HEALTH / REALIZED STRENGTH")


def test_dashboard_has_no_retired_has_or_seeking_rows_without_bond_data():
    rendered = monitor.build_dashboard(
        {"state": "ON"},
        supervisor_pid=None,
        balatro_running=True,
        rows=_rows({}),
        telemetry=None,
    )

    assert "Has             :" not in rendered
    assert "Seeking         :" not in rendered
