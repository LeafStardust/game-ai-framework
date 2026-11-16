from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from games.balatro.env.ppo_campaign import make_ppo_tactical_decision_engine
from games.balatro.env.ppo_candidate_evaluation import fixed_candidate_policy_seed
from games.balatro.env.ppo_full_horizon_tactical_shadow import (
    PPOFullHorizonTacticalShadowError,
    _first_blind_cleared,
    _load_first_blind_production,
    frozen_full_horizon_acceptance,
    make_full_horizon_tactical_reference,
    run_full_horizon_tactical_shadow,
)
from games.balatro.env.seeded_evaluation import FIXED_SEEDED_EPISODES
from games.balatro.live.adaptive_search import LIVE_ADAPTIVE_MAX_HORIZON
from games.balatro.live.hand_action_policy import (
    SEARCH_SCHEDULE_FULL,
    SEARCH_SCHEDULE_SELECTIVE,
)


def _metrics(ante, progress, minimum_cash, terminal_cash):
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


def _episodes(reference_metrics=None):
    production_metrics = _metrics(1, 0.5, 2, 4)
    reference_metrics = reference_metrics or _metrics(2, 0.6, 3, 5)
    values = []
    for spec in FIXED_SEEDED_EPISODES:
        values.append(
            {
                "episode_index": spec.episode_index,
                "game_seed": spec.game_seed,
                "policy_seed": fixed_candidate_policy_seed(spec),
                "production": {
                    "status": "LOSS",
                    "metrics": production_metrics,
                    "first_blind_cleared": spec.episode_index < 62,
                },
                "reference": {
                    "status": "LOSS",
                    "metrics": reference_metrics,
                    "first_blind_cleared": True,
                    "tactical_decision_count": 3,
                    "tactical_elapsed_seconds": 1.5,
                    "maximum_tactical_decision_seconds": 0.75,
                },
            }
        )
    return tuple(values)


def _zero_failures():
    return {
        "illegal_action_count": 0,
        "unsupported_mechanic_count": 0,
        "truncated_episode_count": 0,
        "incomplete_episode_count": 0,
    }


def test_full_horizon_reference_changes_only_the_owned_schedule():
    production = make_ppo_tactical_decision_engine()
    reference = make_full_horizon_tactical_reference()

    assert production.search_schedule_mode == SEARCH_SCHEDULE_SELECTIVE
    assert reference.search_schedule_mode == SEARCH_SCHEDULE_FULL
    assert reference.max_horizon == production.max_horizon == 8
    assert LIVE_ADAPTIVE_MAX_HORIZON == 5
    assert reference.max_search_nodes == production.max_search_nodes == 5000
    assert reference.exact_limit == production.exact_limit == 128
    assert reference.child_exact_limit == production.child_exact_limit == 8
    assert reference.max_search_seconds is production.max_search_seconds is None
    assert type(reference.planner) is type(production.planner)
    assert type(reference.policy) is type(production.policy)
    assert type(reference.planner.evaluator) is type(production.planner.evaluator)
    assert type(reference.planner.action_generator) is type(
        production.planner.action_generator
    )


def test_full_horizon_acceptance_is_frozen_and_paired():
    accepted = frozen_full_horizon_acceptance(_episodes(), _zero_failures())

    assert accepted["accepted"] is True
    assert accepted["decision"] == "accept"
    assert accepted["production_first_blind_clears"] == 62
    assert accepted["reference_first_blind_clears"] == 64
    assert accepted["reference_tactical_decision_count"] == 192
    assert all(accepted["gates"].values())

    regressed = frozen_full_horizon_acceptance(
        _episodes(_metrics(2, 0.6, 1, 3)), _zero_failures()
    )
    assert regressed["accepted"] is False
    assert regressed["gates"]["mean_minimum_cash_nonregression"] is False
    assert regressed["gates"]["mean_terminal_cash_nonregression"] is False

    tied = frozen_full_horizon_acceptance(
        _episodes(_metrics(1, 0.5, 2, 4)), _zero_failures()
    )
    assert tied["accepted"] is False
    assert tied["gates"]["strict_competence_improvement"] is False

    failures = _zero_failures()
    failures["unsupported_mechanic_count"] = 1
    failed_closed = frozen_full_horizon_acceptance(_episodes(), failures)
    assert failed_closed["accepted"] is False
    assert failed_closed["gates"]["zero_fail_closed_outcomes"] is False


def test_full_horizon_acceptance_rejects_reordered_evidence():
    with pytest.raises(
        PPOFullHorizonTacticalShadowError,
        match="incomplete or out of order",
    ):
        frozen_full_horizon_acceptance(
            tuple(reversed(_episodes())), _zero_failures()
        )


def test_full_horizon_loads_exact_published_first_blind_source():
    path = Path("docs/balatro/BALATRO_PPO_TACTICAL_SHADOW_REPORT.json")

    digest, outcomes = _load_first_blind_production(path)

    assert digest == sha256(path.read_bytes()).hexdigest()
    assert len(outcomes) == 64
    assert sum(outcomes.values()) == 62


def test_full_horizon_first_blind_boundary_requires_shop_progress():
    reset = SimpleNamespace(state=SimpleNamespace(phase="BLIND_SELECT"))
    loss = SimpleNamespace(state=SimpleNamespace(phase="GAME_OVER"))
    shop = SimpleNamespace(state=SimpleNamespace(phase="SHOP"))

    assert _first_blind_cleared((reset, shop, loss)) is True
    assert _first_blind_cleared((reset, loss)) is False


def test_full_horizon_rejects_overwrite_before_loading_sources():
    with pytest.raises(PPOFullHorizonTacticalShadowError, match="already exists"):
        run_full_horizon_tactical_shadow(
            "missing-campaign",
            "missing-promotion",
            "missing-first-blind-source",
            __file__,
            maximum_workers=1,
        )


def test_full_horizon_failure_counter_shape_is_exact():
    malformed = deepcopy(_zero_failures())
    malformed["extra"] = 0
    with pytest.raises(
        PPOFullHorizonTacticalShadowError,
        match="failure counters are invalid",
    ):
        frozen_full_horizon_acceptance(_episodes(), malformed)
