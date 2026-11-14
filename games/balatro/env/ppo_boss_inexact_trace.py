"""Production policy-boundary trace for the canonical inexact Boss loss."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path

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
    _plan_payload,
)
from games.balatro.env.ppo_terminal_loss_census import (
    PPO_TERMINAL_LOSS_CENSUS_SCHEMA,
)
from games.balatro.env.seeded_evaluation import (
    FIXED_SEEDED_CORPUS_SHA256,
    FIXED_SEEDED_EPISODES,
)
from games.balatro.live.strategy_hand_policy import _boss_projection_unconfirmed


PPO_BOSS_INEXACT_TRACE_SCHEMA = "balatro-ppo-boss-inexact-boundary-trace-v1"
TERMINAL_CENSUS_SHA256 = (
    "ee4c04bef116d2885890c00ebe86b0bf0496222473d37ff9cc00cac951f859e6"
)
_EPISODE_INDEX = 0
_BOSS_NAME = "The Psychic"
_REQUIREMENT = 600


class PPOBossInexactTraceError(ValueError):
    """Raised when the canonical Boss boundary trace drifts."""


def _load_census(path: str | Path, candidate_sha256: str) -> tuple[dict, dict]:
    content = Path(path).read_bytes()
    if sha256(content).hexdigest() != TERMINAL_CENSUS_SHA256:
        raise PPOBossInexactTraceError("terminal census digest drifted")
    try:
        report = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PPOBossInexactTraceError("terminal census is invalid") from error
    if _canonical_bytes(report) != content:
        raise PPOBossInexactTraceError("terminal census is noncanonical")
    if (
        report.get("schema_version") != PPO_TERMINAL_LOSS_CENSUS_SCHEMA
        or report.get("candidate_sha256") != candidate_sha256
        or report.get("corpus_sha256") != FIXED_SEEDED_CORPUS_SHA256
    ):
        raise PPOBossInexactTraceError("terminal census provenance drifted")
    selected = next(
        (
            item
            for item in report.get("episodes", ())
            if item.get("episode_index") == _EPISODE_INDEX
        ),
        None,
    )
    if (
        selected is None
        or selected.get("classification")
        != "NO_EXACT_CLEAR_WITH_INEXACT_SELECTION"
        or selected.get("game_seed") != FIXED_SEEDED_EPISODES[_EPISODE_INDEX].game_seed
        or selected.get("terminal_blind", {}).get("boss_name") != _BOSS_NAME
        or selected.get("terminal_blind", {}).get("requirement") != _REQUIREMENT
    ):
        raise PPOBossInexactTraceError("canonical inexact Boss episode drifted")
    return report, selected


class _PolicyBoundaryRecorder:
    def __init__(self, policy, events: list[dict[str, object]]) -> None:
        self.policy = policy
        self.events = events
        self.original_decide = policy.decide

    def install(self) -> None:
        original = self.original_decide
        events = self.events

        def recorded(state, plans, **kwargs):
            input_plans = tuple(plans)
            confirmed = kwargs.get("confirmed_clear_path")
            event = {
                "ante": int(state.ante),
                "round": int(state.round),
                "boss_name": state.boss_name,
                "blind_requirement": int(state.blind.requirement),
                "score": int(state.score),
                "hands_remaining": int(state.hands_remaining),
                "discards_remaining": int(state.discards_remaining),
                "boss_projection_unconfirmed": _boss_projection_unconfirmed(
                    state, confirmed
                ),
                "confirmed_clear_path": (
                    None if confirmed is None else _plan_payload(state, confirmed)
                ),
                "input_plans": [_plan_payload(state, plan) for plan in input_plans],
                "completed_search_plans": [
                    _plan_payload(state, plan)
                    for plan in kwargs.get("completed_search_plans", ())
                ],
            }
            decision = original(state, input_plans, **kwargs)
            event["output"] = _decision_payload(state, decision)
            events.append(event)
            return decision

        self.policy.decide = recorded


def _terminal_events(events) -> list[dict[str, object]]:
    selected = [
        event
        for event in events
        if event["boss_name"] == _BOSS_NAME
        and event["blind_requirement"] == _REQUIREMENT
    ]
    if not selected:
        raise PPOBossInexactTraceError("The Psychic policy boundary was not observed")
    return selected


def _first_exact_to_inexact(events) -> int:
    for index, event in enumerate(events):
        if (
            event["boss_projection_unconfirmed"] is True
            and any(plan["exact"] for plan in event["input_plans"])
            and event["output"]["selected_plan"]["exact"] is False
        ):
            return index
    raise PPOBossInexactTraceError("no exact-to-inexact Boss boundary was observed")


def _matches_census_decision(event, census) -> bool:
    selected = event["output"]["selected_plan"]
    expected = census["selected_plan"]
    return event["output"]["action"] == census["action"] and all(
        selected.get(name) == value for name, value in expected.items()
    )


def build_boss_inexact_trace(
    campaign_directory: str | Path,
    promotion_directory: str | Path,
    census_path: str | Path,
) -> dict[str, object]:
    campaign = load_completed_ppo_campaign(campaign_directory)
    identity = PPOCandidateIdentity.from_completed_campaign(campaign)
    final, candidate_source, _ = load_published_fixed_sources(
        campaign, promotion_directory
    )
    _, census_episode = _load_census(census_path, identity.sha256)
    spec = FIXED_SEEDED_EPISODES[_EPISODE_INDEX]
    events: list[dict[str, object]] = []

    def factory(_stream_index):
        engine = make_ppo_tactical_decision_engine()
        _PolicyBoundaryRecorder(engine.policy, events).install()
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
    if evidence.result != candidate_source.episodes[_EPISODE_INDEX]:
        raise PPOBossInexactTraceError("Boss trace replay drifted from published evidence")
    terminal_events = _terminal_events(events)
    census_decisions = census_episode["terminal_decisions"]
    if len(terminal_events) != len(census_decisions) or any(
        not _matches_census_decision(event, census)
        for event, census in zip(terminal_events, census_decisions, strict=True)
    ):
        raise PPOBossInexactTraceError("Boss trace decisions drifted from census")
    first = _first_exact_to_inexact(terminal_events)
    return {
        "schema_version": PPO_BOSS_INEXACT_TRACE_SCHEMA,
        "candidate_sha256": identity.sha256,
        "fixed_candidate_source_sha256": final["artifacts"]["fixed-candidate.json"],
        "terminal_census_sha256": TERMINAL_CENSUS_SHA256,
        "episode_index": _EPISODE_INDEX,
        "game_seed": spec.game_seed,
        "policy_seed": evidence.result.policy_seed,
        "published_status": evidence.result.status.value,
        "published_action_count": evidence.result.action_count,
        "strategic_actions": [
            {"alias": decision.action.alias, "params": decision.action.payload()}
            for decision in evidence.decisions
        ],
        "terminal_blind": census_episode["terminal_blind"],
        "published_metrics": census_episode["metrics"],
        "policy_owner": (
            "games.balatro.live.strategy_hand_policy."
            "StrategyAwareLiveHandActionPolicy.decide"
        ),
        "first_exact_to_inexact_decision_index": first,
        "terminal_decisions": terminal_events,
    }


def write_boss_inexact_trace(report, output_path: str | Path) -> str:
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
    parser.add_argument("census_path")
    parser.add_argument("output_path")
    args = parser.parse_args(argv)
    report = build_boss_inexact_trace(
        args.campaign_directory,
        args.promotion_directory,
        args.census_path,
    )
    digest = write_boss_inexact_trace(report, args.output_path)
    print(json.dumps({
        "output_path": str(Path(args.output_path).resolve()),
        "report_sha256": digest,
        "episode_index": report["episode_index"],
        "game_seed": report["game_seed"],
        "first_exact_to_inexact_decision_index": (
            report["first_exact_to_inexact_decision_index"]
        ),
    }, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
