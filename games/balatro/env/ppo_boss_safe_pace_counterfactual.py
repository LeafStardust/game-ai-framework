"""Single-boundary safe-pace counterfactual for the canonical Psychic loss."""

from __future__ import annotations

import argparse
from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path

from games.balatro.actions import PLAY_CARDS
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


PPO_BOSS_SAFE_PACE_COUNTERFACTUAL_SCHEMA = (
    "balatro-ppo-boss-safe-pace-counterfactual-v1"
)
BOSS_INEXACT_TRACE_SHA256 = (
    "7ddd94f58990dcd1373860028e5df891a6b2305b6ce1c00b9276ad3ab12e3d05"
)
_EPISODE_INDEX = 0
_REQUIREMENT = 600


class PPOBossSafePaceCounterfactualError(ValueError):
    """Raised when the pinned safe-pace counterfactual drifts."""


def _load_boundary_trace(path: str | Path, candidate_sha256: str) -> dict:
    content = Path(path).read_bytes()
    if sha256(content).hexdigest() != BOSS_INEXACT_TRACE_SHA256:
        raise PPOBossSafePaceCounterfactualError("Boss boundary trace digest drifted")
    try:
        report = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PPOBossSafePaceCounterfactualError("Boss boundary trace is invalid") from error
    if _canonical_bytes(report) != content:
        raise PPOBossSafePaceCounterfactualError("Boss boundary trace is noncanonical")
    if (
        report.get("candidate_sha256") != candidate_sha256
        or report.get("episode_index") != _EPISODE_INDEX
        or report.get("first_exact_to_inexact_decision_index") != 0
    ):
        raise PPOBossSafePaceCounterfactualError("Boss boundary trace provenance drifted")
    return report


def _counterfactual_plan(decision_index: int, production):
    if decision_index != 0:
        return None
    plans = [
        plan
        for plan in production.completed_search_plans
        if plan.exact and plan.action.name == PLAY_CARDS
    ]
    if not plans:
        raise PPOBossSafePaceCounterfactualError(
            "pinned safe-pace boundary has no completed exact Play"
        )
    return max(plans, key=lambda plan: float(plan.value.expected_score))


class _CounterfactualEngine:
    def __init__(self, *, counterfactual: bool) -> None:
        self.production = make_ppo_tactical_decision_engine()
        self.counterfactual = counterfactual
        self.decision_index = 0
        self.last = None

    def decide(self, state):
        production = self.production.decide(state)
        selected = production
        override = None
        if self.counterfactual:
            plan = _counterfactual_plan(self.decision_index, production)
            if plan is not None:
                selected = replace(production, action=plan.action, selected_plan=plan)
                override = {
                    "production_action": _decision_payload(state, production)["action"],
                    "exact_play": _decision_payload(state, selected)["selected_plan"],
                }
        self.last = {
            "decision_index": self.decision_index,
            "production": _decision_payload(state, production),
            "selected": _decision_payload(state, selected),
            "override": override,
        }
        self.decision_index += 1
        return selected


def _settle(run, *, counterfactual: bool) -> dict[str, object]:
    engine = _CounterfactualEngine(counterfactual=counterfactual)
    steps = []
    while run.public.phase == "SELECTING_HAND":
        run, evidence = apply_planned_tactical_step_with_evidence(run, engine)
        steps.append({
            "before": _frame(evidence.before),
            "decision": engine.last,
            "after": _frame(evidence.after),
        })
    return {
        "steps": steps,
        "terminal": _frame(run.public),
        "override_count": sum(
            step["decision"]["override"] is not None for step in steps
        ),
    }


def build_boss_safe_pace_counterfactual(
    campaign_directory: str | Path,
    promotion_directory: str | Path,
    boundary_trace_path: str | Path,
) -> dict[str, object]:
    campaign = load_completed_ppo_campaign(campaign_directory)
    identity = PPOCandidateIdentity.from_completed_campaign(campaign)
    final, candidate_source, _ = load_published_fixed_sources(
        campaign, promotion_directory
    )
    boundary_trace = _load_boundary_trace(boundary_trace_path, identity.sha256)
    spec = FIXED_SEEDED_EPISODES[_EPISODE_INDEX]
    published = candidate_source.episodes[_EPISODE_INDEX]
    evidence = execute_ppo_candidate_episode(
        campaign,
        identity,
        evidence_kind=FIXED_EVIDENCE_KIND,
        evidence_sha256=FIXED_SEEDED_CORPUS_SHA256,
        episode_index=spec.episode_index,
        game_seed=spec.game_seed,
        policy_seed=fixed_candidate_policy_seed(spec),
    )
    if evidence.result != published or evidence.result.action_count < 2:
        raise PPOBossSafePaceCounterfactualError("candidate replay drifted")

    backend = PPOHeadlessBackend(make_ppo_tactical_decision_engine())
    environment = BalatroHeadlessEnvironment(backend)
    environment.reset(seed=spec.game_seed)
    for decision in evidence.decisions[:-1]:
        environment.step(decision.action)
    boundary = backend.run
    if (
        boundary.public.phase != "BLIND_SELECT"
        or boundary.public.blind.requirement != _REQUIREMENT
        or boundary.public.boss_name != "The Psychic"
        or evidence.decisions[-1].action.alias != "SELECT_BLIND"
    ):
        raise PPOBossSafePaceCounterfactualError("Psychic boundary drifted")

    activated = select_blind_exact(activate_selected_blind_progression(boundary))
    production = _settle(activated, counterfactual=False)
    counterfactual = _settle(activated, counterfactual=True)
    if (
        production["terminal"]["phase"] != "GAME_OVER"
        or production["terminal"]["score"] != 579
        or counterfactual["override_count"] != 1
    ):
        raise PPOBossSafePaceCounterfactualError("safe-pace outcome drifted")
    return {
        "schema_version": PPO_BOSS_SAFE_PACE_COUNTERFACTUAL_SCHEMA,
        "candidate_sha256": identity.sha256,
        "fixed_candidate_source_sha256": final["artifacts"]["fixed-candidate.json"],
        "boss_boundary_trace_sha256": BOSS_INEXACT_TRACE_SHA256,
        "terminal_census_sha256": boundary_trace["terminal_census_sha256"],
        "episode_index": _EPISODE_INDEX,
        "game_seed": spec.game_seed,
        "policy_seed": evidence.result.policy_seed,
        "strategic_actions": [
            {"alias": item.action.alias, "params": item.action.payload()}
            for item in evidence.decisions
        ],
        "production": production,
        "exact_play_counterfactual": counterfactual,
    }


def write_boss_safe_pace_counterfactual(report, output_path: str | Path) -> str:
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
    parser.add_argument("output_path")
    args = parser.parse_args(argv)
    report = build_boss_safe_pace_counterfactual(
        args.campaign_directory,
        args.promotion_directory,
        args.boundary_trace_path,
    )
    digest = write_boss_safe_pace_counterfactual(report, args.output_path)
    print(json.dumps({
        "output_path": str(Path(args.output_path).resolve()),
        "report_sha256": digest,
        "production_terminal": report["production"]["terminal"],
        "counterfactual_terminal": report["exact_play_counterfactual"]["terminal"],
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
