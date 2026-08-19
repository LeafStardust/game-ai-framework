from games.balatro.live.runtime.balatro_agent_monitor_targets import _strategy_targets


def test_monitor_surfaces_missing_aces_support_targets():
    rows = [
        {
            "event": "observation",
            "data": {
                "state": {
                    "payload": {
                        "jokers": {
                            "cards": [
                                {"label": "Scholar"},
                            ]
                        }
                    }
                }
            },
        },
        {
            "event": "decision",
            "data": {
                "rationale": {
                    "postmortem": {
                        "strategy": {
                            "dominant_strategy_id": "aces",
                        }
                    }
                }
            },
        },
    ]

    targets = _strategy_targets(rows)
    rendered = " | ".join(targets)
    assert "DNA" in rendered
    assert "Fibonacci" in rendered
    assert "Odd Todd" in rendered
    assert "Scholar" not in rendered
