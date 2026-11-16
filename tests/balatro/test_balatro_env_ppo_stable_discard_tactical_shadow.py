from hashlib import sha256
from pathlib import Path

import pytest

from games.balatro.env.ppo_campaign import make_ppo_tactical_decision_engine
from games.balatro.env.ppo_stable_discard_tactical_shadow import (
    PPOStableDiscardTacticalShadowError,
    _load_reproduction_source,
    make_stable_discard_tactical_reference,
    run_stable_discard_tactical_shadow,
)
from games.balatro.live.adaptive_search import LIVE_ADAPTIVE_MAX_HORIZON
from games.balatro.live.hand_action_policy import (
    SEARCH_SCHEDULE_SELECTIVE,
    SEARCH_SCHEDULE_STABLE_DISCARD,
)


def test_stable_discard_reference_changes_only_the_owned_schedule_mode():
    production = make_ppo_tactical_decision_engine()
    reference = make_stable_discard_tactical_reference()

    assert production.search_schedule_mode == SEARCH_SCHEDULE_SELECTIVE
    assert reference.search_schedule_mode == SEARCH_SCHEDULE_STABLE_DISCARD
    assert reference.max_horizon == production.max_horizon == 8
    assert LIVE_ADAPTIVE_MAX_HORIZON == 5
    assert reference.max_search_nodes == production.max_search_nodes == 5000
    assert reference.exact_limit == production.exact_limit == 128
    assert reference.child_exact_limit == production.child_exact_limit == 8
    assert reference.max_search_seconds is production.max_search_seconds is None
    assert type(reference.planner) is type(production.planner)
    assert type(reference.policy) is type(production.policy)
    assert type(reference.planner.evaluator) is type(
        production.planner.evaluator
    )
    assert type(reference.planner.action_generator) is type(
        production.planner.action_generator
    )


def test_stable_discard_loads_exact_current_reproduction_source():
    path = Path(
        "docs/balatro/BALATRO_PPO_CURRENT_TACTICAL_REPRODUCTION.json"
    )

    report, digest = _load_reproduction_source(path)

    assert digest == sha256(path.read_bytes()).hexdigest()
    assert digest == "984ee7441025b6744bba988509bc2fa0ac35765acb85ccc4f77fa8ff42097ec8"
    assert len(report["episodes"]) == 64
    assert report["decision"] == "published-exact"
    assert report["comparison"]["published_mismatch_count"] == 0


def test_stable_discard_rejects_noncanonical_reproduction_source(tmp_path):
    source = Path(
        "docs/balatro/BALATRO_PPO_CURRENT_TACTICAL_REPRODUCTION.json"
    )
    drifted = tmp_path / "drifted.json"
    drifted.write_bytes(source.read_bytes() + b"\n")

    with pytest.raises(
        PPOStableDiscardTacticalShadowError,
        match="provenance drifted",
    ):
        _load_reproduction_source(drifted)


def test_stable_discard_rejects_overwrite_before_loading_sources():
    with pytest.raises(
        PPOStableDiscardTacticalShadowError, match="already exists"
    ):
        run_stable_discard_tactical_shadow(
            "missing-campaign",
            "missing-promotion",
            "missing-reproduction-source",
            __file__,
            maximum_workers=1,
        )
