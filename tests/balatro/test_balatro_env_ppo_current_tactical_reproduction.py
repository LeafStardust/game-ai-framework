from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from games.balatro.env.ppo_campaign import make_ppo_tactical_decision_engine
from games.balatro.env.ppo_candidate_evaluation import fixed_candidate_policy_seed
from games.balatro.env.ppo_current_tactical_reproduction import (
    PPOCurrentTacticalReproductionError,
    _load_full_horizon_source,
    build_reproduction_comparison,
    first_tactical_divergence,
    make_current_selective_tactical_reference,
    run_current_tactical_reproduction,
)
from games.balatro.env.seeded_evaluation import FIXED_SEEDED_EPISODES
from games.balatro.live.hand_action_policy import SEARCH_SCHEDULE_SELECTIVE


def _metrics(*, ante=1, progress=0.5, minimum_cash=2, terminal_cash=4):
    return {
        "frame_count": 3,
        "ante_reached": ante,
        "ante_8_cleared": False,
        "terminal_blind_score": 300.0 * progress,
        "terminal_blind_requirement": 300.0,
        "terminal_chip_margin": 300.0 * progress - 300.0,
        "terminal_requirement_progress": progress,
        "starting_money": 4,
        "minimum_money": minimum_cash,
        "peak_money": max(4, terminal_cash),
        "terminal_money": terminal_cash,
    }


def _decision(*, action="PLAY_CARDS", indices=(0,), score=0):
    return {
        "decision_index": 0,
        "ante": 1,
        "round": 1,
        "boss_name": None,
        "blind_requirement": 300,
        "score": score,
        "hands_remaining": 4,
        "discards_remaining": 3,
        "mode": "PACE_PLAY",
        "action": {"name": action, "indices": list(indices), "target": None},
        "selected_plan": {
            "action": {"name": action, "indices": list(indices), "target": None},
            "horizon": 1,
            "exact": True,
            "candidate_count": 1,
            "value": {
                "clear_probability": 0.0,
                "expected_progress": 0.5,
                "expected_score": 150.0,
                "expected_hands_remaining": 3.0,
                "expected_discards_remaining": 3.0,
                "expected_consumables": 0.0,
            },
        },
        "search_attempts": [],
        "completed_search_plans": [],
        "elapsed_seconds": 0.1,
    }


def _outcome(metrics=None, decision=None):
    decisions = [decision or _decision()]
    return {
        "status": "LOSS",
        "action_count": 3,
        "metrics": metrics or _metrics(),
        "first_blind_cleared": True,
        "tactical_decision_count": len(decisions),
        "tactical_elapsed_seconds": 0.1,
        "maximum_tactical_decision_seconds": 0.1,
        "decisions": decisions,
    }


def _episodes():
    values = []
    for spec in FIXED_SEEDED_EPISODES:
        published = _outcome()
        published.pop("tactical_decision_count")
        published.pop("tactical_elapsed_seconds")
        published.pop("maximum_tactical_decision_seconds")
        published.pop("decisions")
        values.append(
            {
                "episode_index": spec.episode_index,
                "game_seed": spec.game_seed,
                "policy_seed": fixed_candidate_policy_seed(spec),
                "published": published,
                "current_selective": _outcome(),
                "full_horizon": _outcome(
                    _metrics(ante=2, progress=0.6, minimum_cash=3, terminal_cash=5)
                ),
            }
        )
    return tuple(values)


def test_current_selective_reference_is_the_production_factory():
    expected = make_ppo_tactical_decision_engine()
    actual = make_current_selective_tactical_reference()

    assert actual.search_schedule_mode == expected.search_schedule_mode
    assert actual.search_schedule_mode == SEARCH_SCHEDULE_SELECTIVE
    assert actual.max_horizon == expected.max_horizon == 8
    assert actual.max_search_nodes == expected.max_search_nodes == 5000
    assert actual.exact_limit == expected.exact_limit == 128
    assert actual.child_exact_limit == expected.child_exact_limit == 8
    assert actual.max_search_seconds is expected.max_search_seconds is None
    assert type(actual.planner) is type(expected.planner)
    assert type(actual.policy) is type(expected.policy)


def test_first_divergence_requires_the_earliest_shared_state():
    current = _outcome()
    full = _outcome(decision=_decision(action="DISCARD_CARDS", indices=(1, 2)))

    divergence = first_tactical_divergence(current, full)

    assert divergence["kind"] == "tactical_action"
    assert divergence["decision_index"] == 0
    assert divergence["common_state"]["score"] == 0
    assert divergence["current"]["action"]["name"] == "PLAY_CARDS"
    assert divergence["full_horizon"]["action"]["name"] == "DISCARD_CARDS"

    state_drift = _outcome(decision=_decision(score=25))
    divergence = first_tactical_divergence(current, state_drift)
    assert divergence["kind"] == "state_before_tactical_action"
    assert divergence["current_state"]["score"] == 0
    assert divergence["full_horizon_state"]["score"] == 25


def test_reproduction_comparison_separates_published_and_schedule_results():
    comparison = build_reproduction_comparison(_episodes())

    assert comparison["published_reproduction_exact"] is True
    assert comparison["published_mismatch_count"] == 0
    assert comparison["full_horizon_divergence_count"] == 64
    assert comparison["full_horizon_vs_current_selective"]["accepted"] is True

    drifted = list(deepcopy(_episodes()))
    drifted[3]["current_selective"]["metrics"]["terminal_money"] = 3
    comparison = build_reproduction_comparison(tuple(drifted))
    assert comparison["published_reproduction_exact"] is False
    assert comparison["published_mismatch_count"] == 1
    assert comparison["published_mismatches"][0]["episode_index"] == 3


def test_reproduction_comparison_rejects_reordered_corpus():
    with pytest.raises(
        PPOCurrentTacticalReproductionError,
        match="incomplete or out of order",
    ):
        build_reproduction_comparison(tuple(reversed(_episodes())))


def test_full_horizon_source_is_canonical_and_exact():
    path = Path(
        "docs/balatro/BALATRO_PPO_FULL_HORIZON_TACTICAL_SHADOW.json"
    )

    report, digest = _load_full_horizon_source(path)

    assert digest == sha256(path.read_bytes()).hexdigest()
    assert digest == "3147f3b6144303952c3d105444ce0791b9cb8e031b6ae2810b63dd4e1744d77e"
    assert len(report["episodes"]) == 64
    assert report["summary"]["decision"] == "reject"


def test_current_reproduction_rejects_overwrite_before_loading_sources():
    with pytest.raises(
        PPOCurrentTacticalReproductionError, match="already exists"
    ):
        run_current_tactical_reproduction(
            "missing-campaign",
            "missing-promotion",
            "missing-first-blind-source",
            "missing-full-horizon-source",
            __file__,
            maximum_workers=1,
        )
