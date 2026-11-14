"""Digest-bound later-blind tactical attribution for the failed PPO candidate."""

from __future__ import annotations

import argparse
from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path

from games.balatro.env.blind_progression import activate_selected_blind_progression
from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.episode_backend import PPOHeadlessBackend
from games.balatro.env.ppo_campaign import (
    load_completed_ppo_campaign,
    make_ppo_tactical_decision_engine,
)
from games.balatro.env.ppo_candidate_evaluation import (
    FIXED_EVIDENCE_KIND,
    PPOCandidateIdentity,
    execute_ppo_candidate_episode,
    fixed_candidate_policy_seed,
)
from games.balatro.env.ppo_candidate_trace import load_published_fixed_sources
from games.balatro.env.ppo_tactical_failure_trace import (
    _canonical_bytes,
    _decision_payload,
    _frame,
)
from games.balatro.env.seeded_evaluation import (
    FIXED_SEEDED_CORPUS_SHA256,
    FIXED_SEEDED_EPISODES,
)
from games.balatro.env.select_blind import select_blind_exact
from games.balatro.env.tactical_transition import apply_planned_tactical_step_with_evidence


PPO_LATER_TACTICAL_TRACE_SCHEMA = "balatro-ppo-later-tactical-trace-v1"


class PPOLaterTacticalTraceError(ValueError):
    """Raised when later-blind source or replay evidence drifts."""


def _load_diagnostics(final, directory: Path) -> tuple[dict, str]:
    name = "fixed-candidate-diagnostics.json"
    expected = final.get("artifacts", {}).get(name)
    content = (directory / name).read_bytes()
    digest = sha256(content).hexdigest()
    if digest != expected:
        raise PPOLaterTacticalTraceError("fixed candidate diagnostics digest drifted")
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PPOLaterTacticalTraceError("fixed candidate diagnostics are invalid") from error
    if _canonical_bytes(payload) != content:
        raise PPOLaterTacticalTraceError("fixed candidate diagnostics are noncanonical")
    if payload.get("source_sha256") != final["artifacts"]["fixed-candidate.json"]:
        raise PPOLaterTacticalTraceError("fixed candidate diagnostics source drifted")
    return payload, digest


def _distribution(episodes) -> list[dict[str, object]]:
    groups: dict[tuple[int, float], list[float]] = {}
    for item in episodes:
        metrics = item["metrics"]
        key = (int(metrics["ante_reached"]), float(metrics["terminal_blind_requirement"]))
        groups.setdefault(key, []).append(float(metrics["terminal_requirement_progress"]))
    return [
        {
            "ante_reached": ante,
            "terminal_blind_requirement": requirement,
            "episode_count": len(progress),
            "mean_terminal_requirement_progress": sum(progress) / len(progress),
        }
        for (ante, requirement), progress in sorted(groups.items())
    ]


def _representative(diagnostics) -> dict:
    candidates = [
        item for item in diagnostics["episodes"]
        if float(item["metrics"]["terminal_blind_requirement"]) > 300.0
    ]
    if not candidates:
        raise PPOLaterTacticalTraceError("no post-first-blind failure is available")
    return max(
        candidates,
        key=lambda item: (
            float(item["metrics"]["terminal_chip_margin"]),
            -int(item["episode_index"]),
        ),
    )


class _TraceEngine:
    def __init__(self, *, counterfactual: bool) -> None:
        self.base = make_ppo_tactical_decision_engine()
        self.counterfactual = counterfactual
        self.last = None
        self.override = None

    @staticmethod
    def _signature(state, action):
        positions = {id(card): index for index, card in enumerate(state.hand)}
        return {
            "name": action.name,
            "indices": [positions[id(card)] for card in action.cards],
        }

    def decide(self, state):
        production = self.base.decide(state)
        selected = production
        self.override = None
        if self.counterfactual:
            plan = _exact_counterfactual_plan(state, production)
            if plan is not None:
                selected = replace(production, action=plan.action, selected_plan=plan)
                self.override = {
                    "production_action": self._signature(state, production.action),
                    "exact_action": self._signature(state, plan.action),
                    "exact_expected_score": float(plan.value.expected_score),
                    "exact_horizon": plan.horizon,
                }
        self.last = {
            "production": _decision_payload(state, production),
            "selected": _decision_payload(state, selected),
            "override": self.override,
        }
        return selected


def _exact_counterfactual_plan(state, production):
    signature = _TraceEngine._signature
    exact_clears = [
        plan for plan in production.completed_search_plans
        if plan.exact and float(plan.value.clear_probability) == 1.0
        and signature(state, plan.action) != signature(state, production.action)
    ]
    if not exact_clears:
        return None
    return max(exact_clears, key=lambda item: float(item.value.expected_score))


def _settle(run, *, counterfactual: bool) -> dict[str, object]:
    engine = _TraceEngine(counterfactual=counterfactual)
    steps = []
    while run.public.phase == "SELECTING_HAND":
        run, evidence = apply_planned_tactical_step_with_evidence(run, engine)
        steps.append({
            "decision_index": len(steps),
            "before": _frame(evidence.before),
            "decision": engine.last,
            "after": _frame(evidence.after),
        })
    return {
        "steps": steps,
        "terminal": _frame(run.public),
        "override_count": sum(step["decision"]["override"] is not None for step in steps),
    }


def build_later_tactical_trace(campaign_directory: str | Path, promotion_directory: str | Path):
    campaign = load_completed_ppo_campaign(campaign_directory)
    identity = PPOCandidateIdentity.from_completed_campaign(campaign)
    final, candidate_source, _ = load_published_fixed_sources(campaign, promotion_directory)
    directory = Path(promotion_directory)
    diagnostics, diagnostics_sha256 = _load_diagnostics(final, directory)
    selected = _representative(diagnostics)
    index = int(selected["episode_index"])
    spec = FIXED_SEEDED_EPISODES[index]
    published = candidate_source.episodes[index]
    evidence = execute_ppo_candidate_episode(
        campaign,
        identity,
        evidence_kind=FIXED_EVIDENCE_KIND,
        evidence_sha256=FIXED_SEEDED_CORPUS_SHA256,
        episode_index=index,
        game_seed=spec.game_seed,
        policy_seed=fixed_candidate_policy_seed(spec),
    )
    if evidence.result != published or evidence.result.action_count < 2:
        raise PPOLaterTacticalTraceError("representative candidate replay drifted")

    backend = PPOHeadlessBackend(make_ppo_tactical_decision_engine())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=spec.game_seed)
    for decision in evidence.decisions[:-1]:
        environment.step(decision.action)
    boundary = backend.run
    expected_requirement = float(selected["metrics"]["terminal_blind_requirement"])
    if (
        boundary.public.phase != "BLIND_SELECT"
        or float(boundary.public.blind.requirement) != expected_requirement
        or evidence.decisions[-1].action.alias != "SELECT_BLIND"
    ):
        raise PPOLaterTacticalTraceError("representative terminal blind boundary drifted")

    activated = select_blind_exact(activate_selected_blind_progression(boundary))
    production = _settle(activated, counterfactual=False)
    counterfactual = _settle(activated, counterfactual=True)
    if (
        production["terminal"]["phase"] != "GAME_OVER"
        or production["terminal"]["score"] != selected["metrics"]["terminal_blind_score"]
        or counterfactual["terminal"]["phase"] != "ROUND_EVAL"
        or counterfactual["terminal"]["score"] < expected_requirement
        or counterfactual["override_count"] != 1
    ):
        raise PPOLaterTacticalTraceError("later-blind tactical outcome drifted")
    return {
        "schema_version": PPO_LATER_TACTICAL_TRACE_SCHEMA,
        "candidate_sha256": identity.sha256,
        "fixed_candidate_source_sha256": final["artifacts"]["fixed-candidate.json"],
        "diagnostics_source_sha256": diagnostics_sha256,
        "distribution": _distribution(diagnostics["episodes"]),
        "representative": {
            "episode_index": index,
            "game_seed": spec.game_seed,
            "selection": "maximum post-first terminal chip margin, then earliest episode",
            "published_metrics": selected["metrics"],
            "strategic_actions": [
                {"alias": decision.action.alias, "params": decision.action.payload()}
                for decision in evidence.decisions
            ],
            "production": production,
            "exact_counterfactual": counterfactual,
        },
    }


def write_later_tactical_trace(report, output_path: str | Path) -> str:
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
    parser.add_argument("campaign_directory")
    parser.add_argument("promotion_directory")
    parser.add_argument("output_path")
    args = parser.parse_args(argv)
    report = build_later_tactical_trace(args.campaign_directory, args.promotion_directory)
    digest = write_later_tactical_trace(report, args.output_path)
    representative = report["representative"]
    print(json.dumps({
        "output_path": str(Path(args.output_path).resolve()),
        "report_sha256": digest,
        "episode_index": representative["episode_index"],
        "game_seed": representative["game_seed"],
        "production_score": representative["production"]["terminal"]["score"],
        "counterfactual_score": representative["exact_counterfactual"]["terminal"]["score"],
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
