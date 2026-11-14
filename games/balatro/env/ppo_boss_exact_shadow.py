"""Frozen fixed-corpus shadow for preserving computed exact Boss clear paths."""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from hashlib import sha256
import json
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
PPO_BOSS_EXACT_SHADOW_SCHEMA = "balatro-ppo-boss-exact-path-shadow-v1"
_PINNED_EPISODE_INDEX = 1
_PINNED_REQUIREMENT = 600


class PPOBossExactShadowError(ValueError):
    """Raised when Boss exact-path shadow provenance or evidence drifts."""


def _signature(state, action) -> dict[str, object]:
    positions = {id(card): index for index, card in enumerate(state.hand)}
    try:
        indices = [positions[id(card)] for card in action.cards]
    except KeyError as error:
        raise PPOBossExactShadowError("Boss shadow action escaped public state") from error
    return {"name": action.name, "indices": indices}


def select_boss_exact_shadow_decision(state, production):
    blind = getattr(state, "blind", None)
    if getattr(blind, "type", None) is not BlindType.BOSS:
        return production
    production_signature = _signature(state, production.action)
    candidates = [
        plan
        for plan in production.completed_search_plans
        if plan.exact
        and float(plan.value.clear_probability) == 1.0
        and _signature(state, plan.action) != production_signature
    ]
    if not candidates:
        return production
    selected = max(candidates, key=lambda plan: float(plan.value.expected_score))
    return replace(
        production,
        action=selected.action,
        selected_plan=selected,
        rationale=(*production.rationale, "shadow: preserved computed exact Boss clear path"),
    )


class BossExactShadowDecisionEngine:
    def __init__(self, production_engine, events: list[dict[str, object]] | None = None) -> None:
        self.production_engine = production_engine
        self.events = events if events is not None else []

    def decide(self, state):
        production = self.production_engine.decide(state)
        selected = select_boss_exact_shadow_decision(state, production)
        if selected.action is not production.action:
            self.events.append({
                "ante": state.ante,
                "round": state.round,
                "boss_name": state.boss_name,
                "blind_requirement": state.blind.requirement,
                "score": state.score,
                "production_action": _signature(state, production.action),
                "shadow_action": _signature(state, selected.action),
                "clear_probability": float(selected.selected_plan.value.clear_probability),
                "expected_score": float(selected.selected_plan.value.expected_score),
                "horizon": selected.selected_plan.horizon,
                "exact": bool(selected.selected_plan.exact),
            })
        return selected


def _mean(episodes, arm: str, field: str) -> float:
    return sum(float(item[arm]["metrics"][field]) for item in episodes) / len(episodes)


def _acceptance(episodes) -> dict[str, object]:
    canonical_evidence = len(episodes) == len(FIXED_SEEDED_EPISODES) and all(
        item.get("episode_index") == spec.episode_index
        and item.get("game_seed") == spec.game_seed
        and item.get("policy_seed") == fixed_candidate_policy_seed(spec)
        for item, spec in zip(episodes, FIXED_SEEDED_EPISODES, strict=False)
    )
    production_clears = sum(item["production"]["status"] == "ANTE_8_WIN" for item in episodes)
    shadow_clears = sum(item["shadow"]["status"] == "ANTE_8_WIN" for item in episodes)
    pinned = next(
        (item for item in episodes if item.get("episode_index") == _PINNED_EPISODE_INDEX),
        None,
    )
    pinned_club_clear = pinned is not None and any(
        event["blind_requirement"] == _PINNED_REQUIREMENT
        and event["boss_name"] == "The Club"
        and event["exact"] is True
        and event["clear_probability"] == 1.0
        for event in pinned["shadow_events"]
    ) and int(pinned["shadow"]["metrics"]["ante_reached"]) >= 2
    comparisons = {
        "mean_ante_nonregression": _mean(episodes, "shadow", "ante_reached")
        >= _mean(episodes, "production", "ante_reached"),
        "mean_requirement_progress_nonregression": _mean(
            episodes, "shadow", "terminal_requirement_progress"
        ) >= _mean(episodes, "production", "terminal_requirement_progress"),
        "mean_minimum_cash_nonregression": _mean(episodes, "shadow", "minimum_money")
        >= _mean(episodes, "production", "minimum_money"),
        "mean_terminal_cash_nonregression": _mean(episodes, "shadow", "terminal_money")
        >= _mean(episodes, "production", "terminal_money"),
    }
    strict = (
        shadow_clears > production_clears
        or _mean(episodes, "shadow", "ante_reached")
        > _mean(episodes, "production", "ante_reached")
        or _mean(episodes, "shadow", "terminal_requirement_progress")
        > _mean(episodes, "production", "terminal_requirement_progress")
    )
    gates = {
        "complete_canonical_evidence": canonical_evidence,
        "pinned_club_boundary_clears": pinned_club_clear,
        "full_game_clear_count_nonregression": shadow_clears >= production_clears,
        **comparisons,
        "strict_competence_improvement": strict,
    }
    return {
        "production_clear_count": production_clears,
        "shadow_clear_count": shadow_clears,
        "production_mean_ante": _mean(episodes, "production", "ante_reached"),
        "shadow_mean_ante": _mean(episodes, "shadow", "ante_reached"),
        "production_mean_requirement_progress": _mean(
            episodes, "production", "terminal_requirement_progress"
        ),
        "shadow_mean_requirement_progress": _mean(
            episodes, "shadow", "terminal_requirement_progress"
        ),
        "production_mean_minimum_cash": _mean(episodes, "production", "minimum_money"),
        "shadow_mean_minimum_cash": _mean(episodes, "shadow", "minimum_money"),
        "production_mean_terminal_cash": _mean(episodes, "production", "terminal_money"),
        "shadow_mean_terminal_cash": _mean(episodes, "shadow", "terminal_money"),
        "gates": gates,
        "accepted": all(gates.values()),
    }


def build_boss_exact_shadow_report(
    campaign_directory: str | Path, promotion_directory: str | Path
) -> dict[str, object]:
    campaign = load_completed_ppo_campaign(campaign_directory)
    identity = PPOCandidateIdentity.from_completed_campaign(campaign)
    final, candidate_source, _ = load_published_fixed_sources(campaign, promotion_directory)
    diagnostics, diagnostics_sha256 = _load_diagnostics(final, Path(promotion_directory))
    published_metrics = {
        int(item["episode_index"]): item["metrics"] for item in diagnostics["episodes"]
    }
    episodes = []
    for spec, published in zip(FIXED_SEEDED_EPISODES, candidate_source.episodes, strict=True):
        events: list[dict[str, object]] = []

        def factory(_stream_index):
            engine = BossExactShadowDecisionEngine(
                make_ppo_tactical_decision_engine(), events
            )
            return BalatroHeadlessEnvironment(PPOHeadlessBackend(engine))

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
        metrics = derive_terminal_episode_metrics(
            status=evidence.result.status,
            action_count=evidence.result.action_count,
            frames=evidence.frames,
        )
        episodes.append({
            "episode_index": spec.episode_index,
            "game_seed": spec.game_seed,
            "policy_seed": evidence.result.policy_seed,
            "production": {
                "status": published.status.value,
                "action_count": published.action_count,
                "metrics": published_metrics[spec.episode_index],
            },
            "shadow": {
                "status": evidence.result.status.value,
                "action_count": evidence.result.action_count,
                "metrics": asdict(metrics),
            },
            "shadow_events": events,
        })
    summary = _acceptance(episodes)
    return {
        "schema_version": PPO_BOSS_EXACT_SHADOW_SCHEMA,
        "candidate_sha256": identity.sha256,
        "fixed_candidate_source_sha256": final["artifacts"]["fixed-candidate.json"],
        "diagnostics_source_sha256": diagnostics_sha256,
        "corpus_version": FIXED_SEEDED_CORPUS_VERSION,
        "corpus_sha256": FIXED_SEEDED_CORPUS_SHA256,
        "episodes": episodes,
        "summary": summary,
    }


def write_boss_exact_shadow_report(report, output_path: str | Path) -> str:
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
    report = build_boss_exact_shadow_report(
        args.campaign_directory, args.promotion_directory
    )
    digest = write_boss_exact_shadow_report(report, args.output_path)
    print(json.dumps({
        "output_path": str(Path(args.output_path).resolve()),
        "report_sha256": digest,
        "summary": report["summary"],
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
