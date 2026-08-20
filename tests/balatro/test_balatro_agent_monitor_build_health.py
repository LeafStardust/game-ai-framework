import games.balatro.live.runtime.balatro_agent_monitor_targets as monitor


def _rows(build_health):
    return [
        {
            "event": "decision",
            "data": {
                "rationale": {
                    "postmortem": {
                        "strategy": {},
                        "build_health": build_health,
                    }
                }
            },
        }
    ]


def test_build_health_lines_render_deficit_components_and_warning():
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
            "components": [
                {
                    "name": "Hologram",
                    "role": "ENGINE",
                    "realized_engine_id": "hologram",
                },
                {
                    "name": "Banner",
                    "role": "FILLER",
                    "realized_engine_id": None,
                },
            ],
        }
    )

    lines = monitor._build_health_lines(rows)

    assert "Build Health    : 58.0" in lines
    assert "Scaling         : 31.0 [DEFICIT]" in lines
    assert any("Hologram=ENGINE/hologram" in line for line in lines)
    assert any("Banner=FILLER" in line for line in lines)
    assert "Health warnings : Ante 5 scaling deficit" in lines


def test_dashboard_places_health_after_strategy_targets(monkeypatch):
    monkeypatch.setattr(
        monitor,
        "_original_build_dashboard",
        lambda *args, **kwargs: "Strategy        : TEST\nPath            : root > test\nFooter          : ok",
    )
    monkeypatch.setattr(monitor, "_strategy_has", lambda rows: [])
    monkeypatch.setattr(monitor, "_strategy_targets", lambda rows: [])
    rows = _rows(
        {
            "total": 42.0,
            "survival": 10.0,
            "immediate": 20.0,
            "scaling": 50.0,
            "coherence": 50.0,
            "runway": 50.0,
            "critical": True,
            "scaling_deficit": False,
            "warnings": [],
            "components": [],
        }
    )

    rendered = monitor.build_dashboard(
        {},
        supervisor_pid=None,
        balatro_running=True,
        rows=rows,
        telemetry=None,
    )

    assert "Has             : NONE" in rendered
    assert "Seeking         : NONE" in rendered
    assert "Build Health    : 42.0 [CRITICAL]" in rendered
    assert rendered.index("Seeking         : NONE") < rendered.index("Build Health    : 42.0 [CRITICAL]")
