from games.balatro.live.runtime import balatro_agent_monitor as monitor


def _rows():
    return [
        {
            "event": "decision",
            "data": {
                "action": {"name": "PLAY_CARDS"},
                "rationale": {
                    "decision_source": "D1 hand-action policy",
                    "postmortem": {
                        "bond_strategy": {
                            "power_engine": "low_rank_retrigger",
                            "relevant_bonds": [
                                {
                                    "bond_id": "low_rank",
                                    "rank": "R3",
                                    "contribution": 7.0,
                                    "next_rank_threshold": 10.0,
                                    "realization": "ACTIVE",
                                },
                                {
                                    "bond_id": "played_retrigger",
                                    "rank": "R5",
                                    "contribution": 15.0,
                                    "next_rank_threshold": None,
                                    "realization": "MATURE",
                                },
                            ],
                            "composition": {
                                "motifs": [
                                    {
                                        "motif_id": "hack_low_rank",
                                        "state": "ACTIVE",
                                        "missing_components": [],
                                    }
                                ],
                                "synergies": [["low_rank", "played_retrigger"]],
                                "conflicts": [["low_rank", "face_cards"]],
                                "prescriptions": ["prioritize ranks 2-5"],
                            },
                        }
                    },
                },
            },
        }
    ]


def test_monitor_renders_canonical_bond_composition_telemetry() -> None:
    rendered = monitor.build_dashboard(
        {"state": "ON"},
        supervisor_pid=123,
        balatro_running=True,
        rows=_rows(),
        telemetry={},
    )

    assert "STRATEGY / COMPOSITION" in rendered
    assert "Power engine    : Low Rank Retrigger" in rendered
    assert "Low Rank" in rendered
    assert "Rank         : R3" in rendered
    assert "Contribution : 7.0 / 10.0 -> next rank" in rendered
    assert "Realization  : ACTIVE" in rendered
    assert "Played Retrigger" in rendered
    assert "Rank         : R5" in rendered
    assert "Contribution : 15.0 / MAX" in rendered
    assert "Realization  : MATURE" in rendered
    assert "Hack Low Rank=ACTIVE" in rendered
    assert "Low Rank <-> Played Retrigger" in rendered
    assert "Low Rank <-> Face Cards" in rendered
    assert "prioritize ranks 2-5" in rendered


def test_monitor_does_not_reconstruct_retired_strategy_tiers() -> None:
    rendered = monitor.build_dashboard(
        {"state": "ON"},
        supervisor_pid=123,
        balatro_running=True,
        rows=_rows(),
        telemetry={},
    )

    assert "CURRENT STRATEGY" not in rendered
    assert "Has             :" not in rendered
    assert "Seeking         :" not in rendered
    assert "Primary         :" not in rendered
    assert "Secondary       :" not in rendered
    assert "Tertiary        :" not in rendered
