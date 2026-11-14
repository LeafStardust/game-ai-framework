from types import SimpleNamespace

import json
import pytest

from games.balatro.env.ppo_campaign import make_ppo_tactical_decision_engine
from games.balatro.env import ppo_tactical_shadow as shadow_module
from games.balatro.env.ppo_tactical_shadow import (
    PPOTacticalShadowError,
    TacticalShadowDecisionEngine,
    _first_blind,
    build_tactical_shadow_report,
)


def test_completed_search_retention_does_not_change_production_decisions():
    for seed, expected_score in (("5C7469F4", 204), ("FE32359A", 212)):
        result = _first_blind(seed, shadow=False)
        assert result["cleared"] is False
        assert result["score"] == expected_score


def test_frozen_shadow_rule_clears_both_pinned_failures():
    first = _first_blind("5C7469F4", shadow=True)
    second = _first_blind("FE32359A", shadow=True)
    assert (first["cleared"], first["score"]) == (True, 548)
    assert (second["cleared"], second["score"]) == (True, 348)
    assert first["actions"][0]["selected"] == {
        "name": "PLAY_CARDS",
        "indices": [4, 5, 6, 7],
    }
    assert second["actions"][1]["selected"] == {
        "name": "DISCARD_CARDS",
        "indices": [0, 3, 4, 5, 6],
    }
    assert second["actions"][1]["completed_search_plans"][0][
        "clear_probability"
    ] == 0.375


def test_shadow_engine_consumes_only_the_supplied_public_state_and_decision():
    production = make_ppo_tactical_decision_engine()
    shadow = TacticalShadowDecisionEngine(production)
    assert shadow.production_engine is production
    assert not hasattr(shadow, "seed")
    assert not hasattr(shadow, "run")


def test_shadow_report_applies_frozen_paired_acceptance_gates(monkeypatch):
    specs = (
        SimpleNamespace(episode_index=5, game_seed="5C7469F4"),
        SimpleNamespace(episode_index=15, game_seed="FE32359A"),
    )
    monkeypatch.setattr(shadow_module, "FIXED_SEEDED_EPISODES", specs)

    def replay(seed, *, shadow):
        return {
            "cleared": shadow,
            "score": 400 if shadow else 200,
            "requirement": 300,
            "hands_remaining": 1 if shadow else 0,
            "discards_remaining": 1 if shadow else 0,
            "actions": [{"selected": {"name": seed, "indices": [0]}}],
        }

    monkeypatch.setattr(shadow_module, "_first_blind", replay)
    report = build_tactical_shadow_report(
        "docs/balatro/BALATRO_PPO_TACTICAL_FAILURE_TRACE.json"
    )
    assert report["summary"]["production_clear_count"] == 0
    assert report["summary"]["shadow_clear_count"] == 2
    assert report["summary"]["accepted"] is True
    assert all(report["summary"]["gates"].values())


def test_shadow_report_rejects_tactical_source_tampering(tmp_path):
    source = "docs/balatro/BALATRO_PPO_TACTICAL_FAILURE_TRACE.json"
    payload = json.loads(open(source, encoding="utf-8").read())
    payload["episodes"][0]["game_seed"] = "TAMPERED"
    path = tmp_path / "tampered.json"
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    with pytest.raises(PPOTacticalShadowError, match="pinned seeds drifted"):
        build_tactical_shadow_report(path)
