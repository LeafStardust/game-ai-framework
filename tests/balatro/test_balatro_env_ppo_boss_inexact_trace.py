import pytest

from games.balatro.env.ppo_boss_inexact_trace import (
    PPOBossInexactTraceError,
    _first_exact_to_inexact,
    _matches_census_decision,
    _terminal_events,
)


def test_boss_inexact_trace_selects_only_the_pinned_terminal_boundary():
    events = (
        {"boss_name": "The Club", "blind_requirement": 600},
        {"boss_name": "The Psychic", "blind_requirement": 600},
        {"boss_name": "The Psychic", "blind_requirement": 600},
    )
    assert _terminal_events(events) == list(events[1:])


def test_boss_inexact_trace_finds_first_exact_to_inexact_policy_boundary():
    unchanged = {
        "boss_projection_unconfirmed": True,
        "input_plans": [{"exact": False}],
        "output": {"selected_plan": {"exact": False}},
    }
    transition = {
        "boss_projection_unconfirmed": True,
        "input_plans": [{"exact": True}],
        "output": {"selected_plan": {"exact": False}},
    }
    assert _first_exact_to_inexact((unchanged, transition)) == 1


def test_boss_inexact_trace_fails_closed_without_the_boundary():
    event = {
        "boss_projection_unconfirmed": False,
        "input_plans": [{"exact": True}],
        "output": {"selected_plan": {"exact": False}},
    }
    with pytest.raises(PPOBossInexactTraceError, match="exact-to-inexact"):
        _first_exact_to_inexact((event,))


def test_boss_inexact_trace_matches_all_compact_census_fields():
    action = {"name": "PLAY_CARDS", "indices": [0]}
    census = {
        "action": action,
        "selected_plan": {"action": action, "exact": False, "expected_score": 10.0},
    }
    event = {"output": {
        "action": action,
        "selected_plan": {
            **census["selected_plan"],
            "expected_progress": 0.5,
        },
    }}
    assert _matches_census_decision(event, census) is True
    event["output"]["selected_plan"]["expected_score"] = 11.0
    assert _matches_census_decision(event, census) is False
