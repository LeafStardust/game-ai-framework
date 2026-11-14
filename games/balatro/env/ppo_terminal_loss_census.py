"""Digest-bound terminal-blind tactical census for the fixed PPO corpus."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json
import math
import os
from pathlib import Path

from games.balatro.blinds.blind import BlindType
from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.episode_backend import PPOHeadlessBackend
from games.balatro.env.evaluation_diagnostics import derive_terminal_episode_metrics
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
from games.balatro.env.ppo_later_tactical_trace import _load_diagnostics
from games.balatro.env.ppo_tactical_failure_trace import _canonical_bytes
from games.balatro.env.seeded_evaluation import (
    FIXED_SEEDED_CORPUS_SHA256,
    FIXED_SEEDED_CORPUS_VERSION,
    FIXED_SEEDED_EPISODES,
)
from games.balatro.env.state import RunStatus


PPO_TERMINAL_LOSS_CENSUS_SCHEMA = "balatro-ppo-terminal-loss-tactical-census-v1"


class PPOTerminalLossCensusError(ValueError):
    """Raised when terminal-loss census provenance or replay evidence drifts."""


def _signature(state, action) -> dict[str, object]:
    positions = {id(card): index for index, card in enumerate(state.hand)}
    try:
        indices = [positions[id(card)] for card in action.cards]
    except KeyError as error:
        raise PPOTerminalLossCensusError(
            "terminal census action escaped public state"
        ) from error
    return {"name": action.name, "indices": indices}


def _finite(value: object, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise PPOTerminalLossCensusError(f"{name} is non-finite")
    return number


def _plan(state, plan) -> dict[str, object]:
    return {
        "action": _signature(state, plan.action),
        "clear_probability": _finite(
            plan.value.clear_probability, "plan clear probability"
        ),
        "expected_score": _finite(plan.value.expected_score, "plan expected score"),
        "horizon": int(plan.horizon),
        "exact": bool(plan.exact),
    }


def _decision_event(state, decision) -> dict[str, object]:
    selected_signature = _signature(state, decision.action)
    exact_clears = [
        _plan(state, plan)
        for plan in decision.completed_search_plans
        if bool(plan.exact)
        and _finite(plan.value.clear_probability, "completed clear probability") == 1.0
        and _signature(state, plan.action) != selected_signature
    ]
    attempts = [
        {
            "horizon": int(item.horizon),
            "samples": int(item.samples),
            "nodes_evaluated": int(item.nodes_evaluated),
            "max_nodes": int(item.max_nodes),
            "budget_exceeded": bool(item.budget_exceeded),
            "confirmation": bool(item.confirmation),
            "best_exact": item.best_exact,
            "best_clear_probability": item.best_clear_probability,
            "best_expected_score": item.best_expected_score,
        }
        for item in decision.search_attempts
    ]
    blind = state.blind
    return {
        "ante": int(state.ante),
        "round": int(state.round),
        "blind_type": blind.type.value,
        "boss_name": state.boss_name if blind.type is BlindType.BOSS else None,
        "blind_requirement": int(blind.requirement),
        "score": int(state.score),
        "hands_remaining": int(state.hands_remaining),
        "discards_remaining": int(state.discards_remaining),
        "action": selected_signature,
        "selected_plan": _plan(state, decision.selected_plan),
        "completed_search_plan_count": len(decision.completed_search_plans),
        "different_exact_clear_plans": exact_clears,
        "search_attempts": attempts,
    }


class _CensusEngine:
    def __init__(self, production_engine, events: list[dict[str, object]]) -> None:
        self.production_engine = production_engine
        self.events = events

    def decide(self, state):
        decision = self.production_engine.decide(state)
        self.events.append(_decision_event(state, decision))
        return decision


def _terminal_events(events, terminal_state) -> list[dict[str, object]]:
    blind = terminal_state.blind
    selected = [
        event
        for event in events
        if event["ante"] == terminal_state.ante
        and event["round"] == terminal_state.round
        and event["blind_type"] == blind.type.value
        and event["blind_requirement"] == blind.requirement
    ]
    if not selected:
        raise PPOTerminalLossCensusError(
            "terminal loss has no matching public tactical decisions"
        )
    return selected


def _classification(events) -> str:
    if any(event["different_exact_clear_plans"] for event in events):
        return "DIFFERENT_EXACT_CLEAR_AVAILABLE"
    if any(
        attempt["budget_exceeded"]
        for event in events
        for attempt in event["search_attempts"]
    ):
        return "NO_EXACT_CLEAR_WITH_BUDGET_EXHAUSTION"
    if any(not event["selected_plan"]["exact"] for event in events):
        return "NO_EXACT_CLEAR_WITH_INEXACT_SELECTION"
    return "NO_EXACT_CLEAR_WITH_EXACT_SELECTION"


def _counts(values) -> list[dict[str, object]]:
    return [
        {"value": value, "episode_count": count}
        for value, count in sorted(Counter(values).items(), key=lambda item: str(item[0]))
    ]


def _summary(episodes) -> dict[str, object]:
    losses = [item for item in episodes if item["status"] == RunStatus.LOSS.value]
    classes = sorted({item["classification"] for item in losses})
    representatives = []
    for label in classes:
        selected = max(
            (item for item in losses if item["classification"] == label),
            key=lambda item: (
                float(item["metrics"]["terminal_chip_margin"]),
                -int(item["episode_index"]),
            ),
        )
        representatives.append({
            "classification": label,
            "episode_index": selected["episode_index"],
            "game_seed": selected["game_seed"],
            "terminal_chip_margin": selected["metrics"]["terminal_chip_margin"],
        })
    return {
        "episode_count": len(episodes),
        "loss_count": len(losses),
        "win_count": len(episodes) - len(losses),
        "terminal_tactical_decision_count": sum(
            len(item["terminal_decisions"]) for item in losses
        ),
        "episodes_with_different_exact_clear": sum(
            any(event["different_exact_clear_plans"] for event in item["terminal_decisions"])
            for item in losses
        ),
        "episodes_with_budget_exhaustion": sum(
            any(
                attempt["budget_exceeded"]
                for event in item["terminal_decisions"]
                for attempt in event["search_attempts"]
            )
            for item in losses
        ),
        "classification_counts": _counts(item["classification"] for item in losses),
        "blind_type_counts": _counts(item["terminal_blind"]["type"] for item in losses),
        "requirement_counts": _counts(
            item["terminal_blind"]["requirement"] for item in losses
        ),
        "canonical_representatives": representatives,
    }


def build_terminal_loss_census(
    campaign_directory: str | Path, promotion_directory: str | Path
) -> dict[str, object]:
    campaign = load_completed_ppo_campaign(campaign_directory)
    identity = PPOCandidateIdentity.from_completed_campaign(campaign)
    final, candidate_source, _ = load_published_fixed_sources(campaign, promotion_directory)
    diagnostics, diagnostics_sha256 = _load_diagnostics(
        final, Path(promotion_directory)
    )
    published_metrics = {
        int(item["episode_index"]): item["metrics"] for item in diagnostics["episodes"]
    }
    episodes = []
    for spec, published in zip(
        FIXED_SEEDED_EPISODES, candidate_source.episodes, strict=True
    ):
        events: list[dict[str, object]] = []

        def factory(_stream_index):
            return BalatroHeadlessEnvironment(PPOHeadlessBackend(_CensusEngine(
                make_ppo_tactical_decision_engine(), events
            )))

        evidence = execute_ppo_candidate_episode(
            campaign,
            identity,
            evidence_kind=FIXED_EVIDENCE_KIND,
            evidence_sha256=FIXED_SEEDED_CORPUS_SHA256,
            episode_index=spec.episode_index,
            game_seed=spec.game_seed,
            policy_seed=fixed_candidate_policy_seed(spec),
            environment_factory=factory,
        )
        if evidence.result != published:
            raise PPOTerminalLossCensusError(
                "candidate census replay drifted from published evidence"
            )
        metrics = asdict(derive_terminal_episode_metrics(
            status=evidence.result.status,
            action_count=evidence.result.action_count,
            frames=evidence.frames,
        ))
        if metrics != published_metrics[spec.episode_index]:
            raise PPOTerminalLossCensusError(
                "candidate census metrics drifted from published diagnostics"
            )
        terminal = evidence.frames[-1].state
        terminal_decisions = _terminal_events(events, terminal)
        episodes.append({
            "episode_index": spec.episode_index,
            "game_seed": spec.game_seed,
            "policy_seed": evidence.result.policy_seed,
            "status": evidence.result.status.value,
            "action_count": evidence.result.action_count,
            "metrics": metrics,
            "terminal_blind": {
                "ante": terminal.ante,
                "round": terminal.round,
                "type": terminal.blind.type.value,
                "boss_name": (
                    terminal.boss_name
                    if terminal.blind.type is BlindType.BOSS
                    else None
                ),
                "requirement": terminal.blind.requirement,
            },
            "classification": _classification(terminal_decisions),
            "terminal_decisions": terminal_decisions,
        })
    return {
        "schema_version": PPO_TERMINAL_LOSS_CENSUS_SCHEMA,
        "candidate_sha256": identity.sha256,
        "fixed_candidate_source_sha256": final["artifacts"]["fixed-candidate.json"],
        "diagnostics_source_sha256": diagnostics_sha256,
        "corpus_version": FIXED_SEEDED_CORPUS_VERSION,
        "corpus_sha256": FIXED_SEEDED_CORPUS_SHA256,
        "episodes": episodes,
        "summary": _summary(episodes),
    }


def write_terminal_loss_census(report, output_path: str | Path) -> str:
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
    report = build_terminal_loss_census(
        args.campaign_directory, args.promotion_directory
    )
    digest = write_terminal_loss_census(report, args.output_path)
    print(json.dumps({
        "output_path": str(Path(args.output_path).resolve()),
        "report_sha256": digest,
        "summary": report["summary"],
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
