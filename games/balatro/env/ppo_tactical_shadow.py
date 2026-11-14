"""Frozen public-only shadow arbitration experiment for PPO tactical failures."""

from __future__ import annotations

import argparse
from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path

from games.balatro.actions import PLAY_CARDS
from games.balatro.env.blind_progression import activate_selected_blind_progression
from games.balatro.env.episode_backend import pristine_red_white_reset
from games.balatro.env.ppo_campaign import make_ppo_tactical_decision_engine
from games.balatro.env.ppo_tactical_failure_trace import (
    PPO_TACTICAL_FAILURE_TRACE_SCHEMA,
)
from games.balatro.env.seeded_evaluation import (
    FIXED_SEEDED_CORPUS_SHA256,
    FIXED_SEEDED_CORPUS_VERSION,
    FIXED_SEEDED_EPISODES,
)
from games.balatro.env.select_blind import select_blind_exact
from games.balatro.env.tactical_transition import apply_planned_tactical_step_with_evidence
from games.balatro.live.hand_action_policy import PACE_RECOVERY


PPO_TACTICAL_SHADOW_SCHEMA = "balatro-ppo-tactical-arbitration-shadow-v1"
SHADOW_PACE_RATIO_FLOOR = 0.95
SHADOW_CLEAR_PROBABILITY_FLOOR = 0.25
_PINNED_CLEAR_SEEDS = frozenset({"5C7469F4", "FE32359A"})


class PPOTacticalShadowError(ValueError):
    """Raised when shadow evidence, replay, or acceptance drifts."""


def _action_signature(state, action) -> tuple[str, tuple[int, ...]]:
    positions = {id(card): index for index, card in enumerate(state.hand)}
    try:
        return action.name, tuple(positions[id(card)] for card in action.cards)
    except KeyError as error:
        raise PPOTacticalShadowError("shadow action escaped its public state") from error


def select_tactical_shadow_decision(state, production):
    """Apply the frozen v1 rule using production-computed public evidence only."""
    if (
        production.mode == PACE_RECOVERY
        and production.best_play.action.name == PLAY_CARDS
        and float(production.best_play_pace_ratio) >= SHADOW_PACE_RATIO_FLOOR
    ):
        return replace(
            production,
            action=production.best_play.action,
            selected_plan=production.best_play,
            selected_immediate_score=production.best_play_immediate_score,
            selected_pace_ratio=production.best_play_pace_ratio,
            rationale=(*production.rationale, "shadow: accepted near-pace immediate Play"),
        )
    eligible = [
        plan
        for plan in production.completed_search_plans
        if float(plan.value.clear_probability) >= SHADOW_CLEAR_PROBABILITY_FLOOR
    ]
    if not eligible:
        return production
    selected = max(
        eligible,
        key=lambda plan: (
            float(plan.value.clear_probability),
            float(plan.value.expected_score),
            float(plan.value.expected_hands_remaining),
            float(plan.value.expected_discards_remaining),
        ),
    )
    _action_signature(state, selected.action)
    return replace(
        production,
        action=selected.action,
        selected_plan=selected,
        selected_immediate_score=None,
        selected_pace_ratio=None,
        rationale=(*production.rationale, "shadow: accepted graded adaptive clear evidence"),
    )


class TacticalShadowDecisionEngine:
    def __init__(self, production_engine) -> None:
        self.production_engine = production_engine

    def decide(self, state):
        return select_tactical_shadow_decision(
            state, self.production_engine.decide(state)
        )


class _ActionRecorder:
    def __init__(self, engine) -> None:
        self.engine = engine
        self.actions: list[dict[str, object]] = []

    def decide(self, state):
        decision = self.engine.decide(state)
        name, indices = _action_signature(state, decision.action)
        completed = []
        for plan in decision.completed_search_plans:
            plan_name, plan_indices = _action_signature(state, plan.action)
            completed.append({
                "action": {"name": plan_name, "indices": list(plan_indices)},
                "clear_probability": float(plan.value.clear_probability),
                "expected_score": float(plan.value.expected_score),
                "expected_hands_remaining": float(plan.value.expected_hands_remaining),
                "expected_discards_remaining": float(plan.value.expected_discards_remaining),
                "exact": bool(plan.exact),
                "horizon": plan.horizon,
            })
        self.actions.append({
            "selected": {"name": name, "indices": list(indices)},
            "completed_search_plans": completed,
        })
        return decision


def _first_blind(seed: str, *, shadow: bool) -> dict[str, object]:
    engine = make_ppo_tactical_decision_engine()
    if shadow:
        engine = TacticalShadowDecisionEngine(engine)
    recorder = _ActionRecorder(engine)
    run = select_blind_exact(
        activate_selected_blind_progression(pristine_red_white_reset(seed))
    )
    while run.public.phase == "SELECTING_HAND":
        run, _ = apply_planned_tactical_step_with_evidence(run, recorder)
    state = run.public
    if state.phase not in {"ROUND_EVAL", "GAME_OVER"}:
        raise PPOTacticalShadowError("first-blind replay ended at an invalid phase")
    requirement = state.blind.requirement
    cleared = state.phase == "ROUND_EVAL" and state.score >= requirement
    if (state.phase == "ROUND_EVAL") != cleared:
        raise PPOTacticalShadowError("first-blind clear boundary is inconsistent")
    return {
        "cleared": cleared,
        "score": state.score,
        "requirement": requirement,
        "hands_remaining": state.hands_remaining,
        "discards_remaining": state.discards_remaining,
        "actions": recorder.actions,
    }


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise PPOTacticalShadowError("shadow report is not canonical JSON") from error


def _source_digest(path: str | Path) -> str:
    content = Path(path).read_bytes()
    try:
        payload = json.loads(content.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PPOTacticalShadowError("tactical trace source is unreadable") from error
    if _canonical_bytes(payload) != content:
        raise PPOTacticalShadowError("tactical trace source is not canonical")
    if payload.get("schema_version") != PPO_TACTICAL_FAILURE_TRACE_SCHEMA:
        raise PPOTacticalShadowError("tactical trace source schema drifted")
    if {item.get("game_seed") for item in payload.get("episodes", ())} != _PINNED_CLEAR_SEEDS:
        raise PPOTacticalShadowError("tactical trace pinned seeds drifted")
    return sha256(content).hexdigest()


def build_tactical_shadow_report(source_path: str | Path) -> dict[str, object]:
    source_sha256 = _source_digest(source_path)
    episodes = []
    for spec in FIXED_SEEDED_EPISODES:
        production = _first_blind(spec.game_seed, shadow=False)
        shadow = _first_blind(spec.game_seed, shadow=True)
        episodes.append({
            "episode_index": spec.episode_index,
            "game_seed": spec.game_seed,
            "production": production,
            "shadow": shadow,
        })
    production_clears = sum(item["production"]["cleared"] for item in episodes)
    shadow_clears = sum(item["shadow"]["cleared"] for item in episodes)
    count = len(episodes)
    mean = lambda arm, field: sum(float(item[arm][field]) for item in episodes) / count
    pinned = {
        item["game_seed"]: bool(item["shadow"]["cleared"])
        for item in episodes
        if item["game_seed"] in _PINNED_CLEAR_SEEDS
    }
    gates = {
        "pinned_failures_clear": set(pinned) == _PINNED_CLEAR_SEEDS and all(pinned.values()),
        "clear_count_strictly_improves": shadow_clears > production_clears,
        "mean_terminal_score_nonregression": mean("shadow", "score") >= mean("production", "score"),
        "mean_hands_nonregression": mean("shadow", "hands_remaining") >= mean("production", "hands_remaining"),
        "mean_discards_nonregression": mean("shadow", "discards_remaining") >= mean("production", "discards_remaining"),
    }
    return {
        "schema_version": PPO_TACTICAL_SHADOW_SCHEMA,
        "source_trace_sha256": source_sha256,
        "corpus_version": FIXED_SEEDED_CORPUS_VERSION,
        "corpus_sha256": FIXED_SEEDED_CORPUS_SHA256,
        "pace_ratio_floor": SHADOW_PACE_RATIO_FLOOR,
        "clear_probability_floor": SHADOW_CLEAR_PROBABILITY_FLOOR,
        "episodes": episodes,
        "summary": {
            "production_clear_count": production_clears,
            "shadow_clear_count": shadow_clears,
            "production_mean_score": mean("production", "score"),
            "shadow_mean_score": mean("shadow", "score"),
            "production_mean_hands_remaining": mean("production", "hands_remaining"),
            "shadow_mean_hands_remaining": mean("shadow", "hands_remaining"),
            "production_mean_discards_remaining": mean("production", "discards_remaining"),
            "shadow_mean_discards_remaining": mean("shadow", "discards_remaining"),
            "gates": gates,
            "accepted": all(gates.values()),
        },
    }


def write_tactical_shadow_report(report: dict[str, object], output_path: str | Path) -> str:
    content = _canonical_bytes(report)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return sha256(content).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tactical_trace")
    parser.add_argument("output_path")
    args = parser.parse_args(argv)
    report = build_tactical_shadow_report(args.tactical_trace)
    digest = write_tactical_shadow_report(report, args.output_path)
    print(json.dumps({
        "output_path": str(Path(args.output_path).resolve()),
        "report_sha256": digest,
        "summary": report["summary"],
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
