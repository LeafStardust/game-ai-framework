"""One-decision exact-plan sweep for the canonical Psychic loss."""

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
from games.balatro.env.ppo_boss_safe_pace_counterfactual import (
    BOSS_INEXACT_TRACE_SHA256,
    _load_boundary_trace,
)
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


PPO_BOSS_SAFE_PACE_SWEEP_SCHEMA = "balatro-ppo-boss-safe-pace-sweep-v1"
DECISION_ZERO_REPORT_SHA256 = (
    "360b992c29d4a5bf7fccec57807aa915fd8a8564beab4f8615b6b3fb39781985"
)
_EPISODE_INDEX = 0
_PRODUCTION_SCORE = 579


class PPOBossSafePaceSweepError(ValueError):
    """Raised when the fixed Psychic one-decision sweep drifts."""


def _load_decision_zero_report(path: str | Path, candidate_sha256: str) -> dict:
    content = Path(path).read_bytes()
    if sha256(content).hexdigest() != DECISION_ZERO_REPORT_SHA256:
        raise PPOBossSafePaceSweepError("decision-0 report digest drifted")
    try:
        report = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PPOBossSafePaceSweepError("decision-0 report is invalid") from error
    if _canonical_bytes(report) != content:
        raise PPOBossSafePaceSweepError("decision-0 report is noncanonical")
    if (
        report.get("candidate_sha256") != candidate_sha256
        or report.get("boss_boundary_trace_sha256") != BOSS_INEXACT_TRACE_SHA256
        or report.get("production", {}).get("terminal", {}).get("score")
        != _PRODUCTION_SCORE
    ):
        raise PPOBossSafePaceSweepError("decision-0 report provenance drifted")
    return report


def _eligible_indices(boundary_trace) -> tuple[int, ...]:
    eligible = []
    for index, event in enumerate(boundary_trace["terminal_decisions"]):
        production = event["output"]["action"]
        if index > 0 and any(
            plan["exact"] and plan["action"] != production
            for plan in event["completed_search_plans"]
        ):
            eligible.append(index)
    if not eligible:
        raise PPOBossSafePaceSweepError("no later exact-plan substitutions exist")
    return tuple(eligible)


def _different_exact_plan(state, production):
    payload = _decision_payload(state, production)
    signature = payload["action"]
    candidates = [
        plan
        for plan in production.completed_search_plans
        if plan.exact and _decision_payload(
            state, replace(production, action=plan.action, selected_plan=plan)
        )["action"] != signature
    ]
    if not candidates:
        raise PPOBossSafePaceSweepError("target decision has no different exact plan")
    return max(candidates, key=lambda plan: float(plan.value.expected_score))


class _SweepEngine:
    def __init__(self, target_index: int) -> None:
        self.production = make_ppo_tactical_decision_engine()
        self.target_index = target_index
        self.decision_index = 0
        self.last = None

    def decide(self, state):
        production = self.production.decide(state)
        selected = production
        override = None
        if self.decision_index == self.target_index:
            plan = _different_exact_plan(state, production)
            selected = replace(production, action=plan.action, selected_plan=plan)
            override = {
                "production_action": _decision_payload(state, production)["action"],
                "exact_plan": _decision_payload(state, selected)["selected_plan"],
            }
        self.last = {
            "decision_index": self.decision_index,
            "production": _decision_payload(state, production),
            "selected": _decision_payload(state, selected),
            "override": override,
        }
        self.decision_index += 1
        return selected


def _settle(run, target_index: int) -> dict[str, object]:
    engine = _SweepEngine(target_index)
    steps = []
    while run.public.phase == "SELECTING_HAND":
        run, evidence = apply_planned_tactical_step_with_evidence(run, engine)
        steps.append({
            "before": _frame(evidence.before),
            "decision": engine.last,
            "after": _frame(evidence.after),
        })
    result = {
        "target_decision_index": target_index,
        "steps": steps,
        "terminal": _frame(run.public),
        "override_count": sum(
            step["decision"]["override"] is not None for step in steps
        ),
    }
    if result["override_count"] != 1:
        raise PPOBossSafePaceSweepError("sweep arm did not apply exactly one override")
    return result


def build_boss_safe_pace_sweep(
    campaign_directory: str | Path,
    promotion_directory: str | Path,
    boundary_trace_path: str | Path,
    decision_zero_path: str | Path,
) -> dict[str, object]:
    campaign = load_completed_ppo_campaign(campaign_directory)
    identity = PPOCandidateIdentity.from_completed_campaign(campaign)
    final, candidate_source, _ = load_published_fixed_sources(
        campaign, promotion_directory
    )
    boundary_trace = _load_boundary_trace(boundary_trace_path, identity.sha256)
    decision_zero = _load_decision_zero_report(decision_zero_path, identity.sha256)
    spec = FIXED_SEEDED_EPISODES[_EPISODE_INDEX]
    evidence = execute_ppo_candidate_episode(
        campaign,
        identity,
        evidence_kind=FIXED_EVIDENCE_KIND,
        evidence_sha256=FIXED_SEEDED_CORPUS_SHA256,
        episode_index=spec.episode_index,
        game_seed=spec.game_seed,
        policy_seed=fixed_candidate_policy_seed(spec),
    )
    if evidence.result != candidate_source.episodes[_EPISODE_INDEX]:
        raise PPOBossSafePaceSweepError("candidate sweep replay drifted")

    backend = PPOHeadlessBackend(make_ppo_tactical_decision_engine())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=spec.game_seed)
    for decision in evidence.decisions[:-1]:
        environment.step(decision.action)
    boundary = backend.run
    if (
        boundary.public.phase != "BLIND_SELECT"
        or boundary.public.blind.requirement != 600
        or boundary.public.boss_name != "The Psychic"
    ):
        raise PPOBossSafePaceSweepError("Psychic sweep boundary drifted")
    activated = select_blind_exact(activate_selected_blind_progression(boundary))
    arms = [_settle(activated, index) for index in _eligible_indices(boundary_trace)]
    for arm in arms:
        arm["terminal_score_delta"] = arm["terminal"]["score"] - _PRODUCTION_SCORE
    return {
        "schema_version": PPO_BOSS_SAFE_PACE_SWEEP_SCHEMA,
        "candidate_sha256": identity.sha256,
        "fixed_candidate_source_sha256": final["artifacts"]["fixed-candidate.json"],
        "boss_boundary_trace_sha256": BOSS_INEXACT_TRACE_SHA256,
        "decision_zero_report_sha256": DECISION_ZERO_REPORT_SHA256,
        "terminal_census_sha256": decision_zero["terminal_census_sha256"],
        "episode_index": _EPISODE_INDEX,
        "game_seed": spec.game_seed,
        "policy_seed": evidence.result.policy_seed,
        "production_terminal": decision_zero["production"]["terminal"],
        "arms": arms,
    }


def write_boss_safe_pace_sweep(report, output_path: str | Path) -> str:
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
    parser.add_argument("boundary_trace_path")
    parser.add_argument("decision_zero_path")
    parser.add_argument("output_path")
    args = parser.parse_args(argv)
    report = build_boss_safe_pace_sweep(
        args.campaign_directory,
        args.promotion_directory,
        args.boundary_trace_path,
        args.decision_zero_path,
    )
    digest = write_boss_safe_pace_sweep(report, args.output_path)
    print(json.dumps({
        "output_path": str(Path(args.output_path).resolve()),
        "report_sha256": digest,
        "score_deltas": [
            {
                "decision_index": arm["target_decision_index"],
                "terminal_score": arm["terminal"]["score"],
                "delta": arm["terminal_score_delta"],
            }
            for arm in report["arms"]
        ],
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
