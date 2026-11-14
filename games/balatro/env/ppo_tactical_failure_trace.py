"""Digest-bound tactical traces for the fixed PPO first-blind failures."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
from typing import Any

from games.balatro.actions import BalatroAction
from games.balatro.env.blind_progression import activate_selected_blind_progression
from games.balatro.env.episode_backend import pristine_red_white_reset
from games.balatro.env.ppo_campaign import make_ppo_tactical_decision_engine
from games.balatro.env.select_blind import select_blind_exact
from games.balatro.env.tactical_transition import apply_planned_tactical_step_with_evidence


PPO_TACTICAL_FAILURE_TRACE_SCHEMA = "balatro-ppo-tactical-failure-trace-v1"
PPO_CANDIDATE_TRACE_SCHEMA = "balatro-ppo-candidate-fixed-trace-v1"
_EXPECTED = {
    "5C7469F4": (5, 204),
    "FE32359A": (15, 212),
}
_CLEARING_LINES = {
    "5C7469F4": (
        ("PLAY_CARDS", (2, 4, 5, 6, 7)),
        ("PLAY_CARDS", (0, 1, 2, 3, 4)),
    ),
    "FE32359A": (
        ("DISCARD_CARDS", (0, 2, 3, 6, 7)),
        ("DISCARD_CARDS", (0, 3, 4, 5, 6)),
        ("DISCARD_CARDS", (1, 4, 5, 6, 7)),
        ("PLAY_CARDS", (1, 2, 4, 5)),
        ("PLAY_CARDS", (0,)),
        ("PLAY_CARDS", (3, 4, 5, 6, 7)),
    ),
}


class PPOTacticalFailureTraceError(ValueError):
    """Raised when tactical diagnostic provenance or replay drifts."""


def _canonical_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise PPOTacticalFailureTraceError("tactical trace is not canonical JSON") from error


def _action_payload(state, action: BalatroAction) -> dict[str, object]:
    positions = {id(card): index for index, card in enumerate(state.hand)}
    try:
        indices = tuple(positions[id(card)] for card in action.cards)
    except KeyError as error:
        raise PPOTacticalFailureTraceError("tactical action escaped its observation") from error
    return {"name": action.name, "indices": list(indices)}


def _frame(state) -> dict[str, object]:
    blind = state.blind
    return {
        "phase": state.phase,
        "ante": state.ante,
        "round": state.round,
        "score": state.score,
        "blind_requirement": None if blind is None else blind.requirement,
        "hands_remaining": state.hands_remaining,
        "discards_remaining": state.discards_remaining,
        "hand": [
            {
                "rank": card.rank,
                "suit": card.suit,
                "face_down": bool(card.face_down),
                "debuffed": bool(card.debuffed),
            }
            for card in state.hand
        ],
    }


def _plan_payload(state, plan) -> dict[str, object]:
    value = plan.value
    numbers = (
        value.clear_probability,
        value.expected_progress,
        value.expected_score,
        value.expected_hands_remaining,
        value.expected_discards_remaining,
    )
    if not all(math.isfinite(float(number)) for number in numbers):
        raise PPOTacticalFailureTraceError("tactical plan contains a non-finite value")
    return {
        "action": _action_payload(state, plan.action),
        "clear_probability": float(value.clear_probability),
        "expected_progress": float(value.expected_progress),
        "expected_score": float(value.expected_score),
        "expected_hands_remaining": float(value.expected_hands_remaining),
        "expected_discards_remaining": float(value.expected_discards_remaining),
        "exact": bool(plan.exact),
        "horizon": plan.horizon,
    }


def _decision_payload(state, decision) -> dict[str, object]:
    return {
        "mode": decision.mode,
        "action": _action_payload(state, decision.action),
        "selected_plan": _plan_payload(state, decision.selected_plan),
        "plans": [_plan_payload(state, plan) for plan in decision.plans],
        "pace_target": float(decision.pace_target),
        "best_play_immediate_score": float(decision.best_play_immediate_score),
        "best_play_pace_ratio": float(decision.best_play_pace_ratio),
        "selected_immediate_score": decision.selected_immediate_score,
        "selected_pace_ratio": decision.selected_pace_ratio,
        "confidence": float(decision.confidence),
        "rationale": list(decision.rationale),
        "search_attempts": [
            {
                "horizon": item.horizon,
                "samples": item.samples,
                "nodes_evaluated": item.nodes_evaluated,
                "max_nodes": item.max_nodes,
                "budget_exceeded": item.budget_exceeded,
                "best_action": item.best_action,
                "best_clear_probability": item.best_clear_probability,
                "best_expected_score": item.best_expected_score,
                "best_exact": item.best_exact,
            }
            for item in decision.search_attempts
        ],
    }


class _RecordingEngine:
    def __init__(self, engine) -> None:
        self.engine = engine
        self.record: dict[str, object] | None = None

    def decide(self, state):
        decision = self.engine.decide(state)
        self.record = _decision_payload(state, decision)
        return decision


class _IndexedLineEngine:
    def __init__(self, line: tuple[tuple[str, tuple[int, ...]], ...]) -> None:
        self.line = line
        self.index = 0

    def decide(self, state):
        if self.index >= len(self.line):
            raise PPOTacticalFailureTraceError("clearing line ended before the blind")
        name, indices = self.line[self.index]
        self.index += 1
        if not indices or any(index < 0 or index >= len(state.hand) for index in indices):
            raise PPOTacticalFailureTraceError("clearing line contains an invalid hand index")
        return type("IndexedTacticalDecision", (), {
            "action": BalatroAction(name, cards=[state.hand[index] for index in indices])
        })()


def _activated_run(seed: str):
    return select_blind_exact(
        activate_selected_blind_progression(pristine_red_white_reset(seed))
    )


def _production_trace(seed: str) -> dict[str, object]:
    recorder = _RecordingEngine(make_ppo_tactical_decision_engine())
    run = _activated_run(seed)
    steps = []
    while run.public.phase == "SELECTING_HAND":
        run, evidence = apply_planned_tactical_step_with_evidence(run, recorder)
        if recorder.record is None:
            raise PPOTacticalFailureTraceError("production decision was not recorded")
        steps.append({
            "decision_index": len(steps),
            "before": _frame(evidence.before),
            "decision": recorder.record,
            "after": _frame(evidence.after),
        })
        recorder.record = None
    return {"steps": steps, "terminal": _frame(run.public)}


def _clearing_trace(seed: str) -> dict[str, object]:
    engine = _IndexedLineEngine(_CLEARING_LINES[seed])
    run = _activated_run(seed)
    steps = []
    while run.public.phase == "SELECTING_HAND":
        run, evidence = apply_planned_tactical_step_with_evidence(run, engine)
        steps.append({
            "decision_index": len(steps),
            "action": {
                "name": evidence.action.name,
                "indices": list(evidence.selected_hand_indices),
            },
            "before": _frame(evidence.before),
            "after": _frame(evidence.after),
        })
    if engine.index != len(engine.line):
        raise PPOTacticalFailureTraceError("clearing line has unused decisions")
    requirement = run.public.blind.requirement
    if run.public.phase != "ROUND_EVAL" or run.public.score < requirement:
        raise PPOTacticalFailureTraceError("indexed counterfactual did not clear exactly")
    return {"steps": steps, "terminal": _frame(run.public)}


def _load_source(path: str | Path) -> tuple[dict[str, Any], str]:
    content = Path(path).read_bytes()
    try:
        payload = json.loads(content.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PPOTacticalFailureTraceError("candidate trace source is unreadable") from error
    if _canonical_bytes(payload) != content:
        raise PPOTacticalFailureTraceError("candidate trace source is not canonical")
    if payload.get("schema_version") != PPO_CANDIDATE_TRACE_SCHEMA:
        raise PPOTacticalFailureTraceError("candidate trace source schema drifted")
    by_seed = {item.get("game_seed"): item for item in payload.get("episodes", ())}
    for seed, (episode_index, terminal_score) in _EXPECTED.items():
        item = by_seed.get(seed)
        if (
            not isinstance(item, dict)
            or item.get("episode_index") != episode_index
            or item.get("expected_status") != "LOSS"
            or item.get("expected_action_count") != 1
            or item.get("frames", [{}])[-1].get("score") != terminal_score
        ):
            raise PPOTacticalFailureTraceError("candidate tactical source drifted")
    return payload, sha256(content).hexdigest()


def build_tactical_failure_trace(source_path: str | Path) -> dict[str, object]:
    _, source_sha256 = _load_source(source_path)
    episodes = []
    for seed, (episode_index, terminal_score) in _EXPECTED.items():
        production = _production_trace(seed)
        if production["terminal"]["phase"] != "GAME_OVER" or production["terminal"]["score"] != terminal_score:
            raise PPOTacticalFailureTraceError("production tactical replay drifted")
        counterfactual = _clearing_trace(seed)
        production_actions = [step["decision"]["action"] for step in production["steps"]]
        clearing_actions = [step["action"] for step in counterfactual["steps"]]
        divergence = next(
            (index for index, pair in enumerate(zip(production_actions, clearing_actions)) if pair[0] != pair[1]),
            min(len(production_actions), len(clearing_actions)),
        )
        episodes.append({
            "episode_index": episode_index,
            "game_seed": seed,
            "first_divergence_index": divergence,
            "production": production,
            "exact_clearing_counterfactual": counterfactual,
        })
    return {
        "schema_version": PPO_TACTICAL_FAILURE_TRACE_SCHEMA,
        "candidate_trace_source_sha256": source_sha256,
        "episodes": episodes,
    }


def write_tactical_failure_trace(report: dict[str, object], output_path: str | Path) -> str:
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
    parser.add_argument("candidate_trace")
    parser.add_argument("output_path")
    args = parser.parse_args(argv)
    report = build_tactical_failure_trace(args.candidate_trace)
    digest = write_tactical_failure_trace(report, args.output_path)
    print(json.dumps({
        "output_path": str(Path(args.output_path).resolve()),
        "report_sha256": digest,
        "episodes": [
            {
                "episode_index": item["episode_index"],
                "game_seed": item["game_seed"],
                "first_divergence_index": item["first_divergence_index"],
                "production_score": item["production"]["terminal"]["score"],
                "clearing_score": item["exact_clearing_counterfactual"]["terminal"]["score"],
            }
            for item in report["episodes"]
        ],
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
