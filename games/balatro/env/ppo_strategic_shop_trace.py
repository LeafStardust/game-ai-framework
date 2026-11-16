"""Exact fixed-corpus strategic and shop attribution for the trained PPO."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from hashlib import sha256
import json
import math
import multiprocessing
from pathlib import Path
from statistics import fmean
from typing import Any, Callable

from games.balatro.env.action_encoding import (
    PUBLIC_ACTION_SCHEMA,
    PUBLIC_ACTION_VERSION,
    action_from_index,
)
from games.balatro.env.actions import EnvAction
from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.episode_backend import PPOHeadlessBackend
from games.balatro.env.evaluation_diagnostics import derive_terminal_episode_metrics
from games.balatro.env.observation_encoding import PUBLIC_OBSERVATION_VERSION
from games.balatro.env.ppo_campaign import (
    CompletedPPOCampaign,
    _atomic_write,
    _canonical_bytes,
    load_completed_ppo_campaign,
    make_ppo_tactical_decision_engine,
)
from games.balatro.env.ppo_candidate_evaluation import (
    FIXED_EVIDENCE_KIND,
    PPOCandidateDecision,
    PPOCandidateIdentity,
    execute_ppo_candidate_episode,
    fixed_candidate_policy_seed,
)
from games.balatro.env.ppo_current_tactical_reproduction import (
    PPO_CURRENT_TACTICAL_REPRODUCTION_SCHEMA,
)
from games.balatro.env.ppo_full_horizon_tactical_shadow import (
    _first_blind_cleared,
)
from games.balatro.env.ppo_promotion_evaluation import FINAL_ARTIFACT_NAME
from games.balatro.env.seeded_evaluation import (
    FIXED_SEEDED_CORPUS_SHA256,
    FIXED_SEEDED_CORPUS_VERSION,
    FIXED_SEEDED_EPISODES,
    FixedSeededEpisodeSpec,
)
from games.balatro.env.serialization import _shop_item_payload
from games.balatro.env.state import EnvStateFrame
from games.balatro.env.transition import HeadlessRunState
from games.balatro.live.hand_action_policy import SEARCH_SCHEDULE_SELECTIVE


PPO_STRATEGIC_SHOP_TRACE_SCHEMA = "balatro-red-white-ppo-strategic-shop-trace-v1"
PPO_STRATEGIC_SHOP_TRACE_REPORT_NAME = "strategic_shop_trace.json"
CURRENT_REPRODUCTION_SHA256 = (
    "984ee7441025b6744bba988509bc2fa0ac35765acb85ccc4f77fa8ff42097ec8"
)
_PURCHASE_ALIASES = frozenset(
    {"BUY_JOKER", "BUY_VOUCHER", "BUY_CONSUMABLE", "OPEN_PACK"}
)
_SHOP_TRACE_ALIASES = _PURCHASE_ALIASES | {"END_SHOP", "REROLL_SHOP"}


class PPOStrategicShopTraceError(ValueError):
    """Raised when strategic trace provenance or exact replay drifts."""


def _action_dict(action: EnvAction) -> dict[str, Any]:
    if not isinstance(action, EnvAction):
        raise TypeError("strategic trace action must be EnvAction")
    return {"alias": action.alias, "params": dict(action.params)}


def _frame_dict(frame: EnvStateFrame) -> dict[str, Any]:
    if not isinstance(frame, EnvStateFrame):
        raise TypeError("strategic trace frame must be EnvStateFrame")
    state = frame.state
    blind = state.blind
    return {
        "phase": state.phase,
        "ante": state.ante,
        "round": state.round,
        "money": state.money,
        "score": state.score,
        "hands_remaining": state.hands_remaining,
        "discards_remaining": state.discards_remaining,
        "hand_size": state.hand_size,
        "shop_active": state.shop_active,
        "boss_name": state.boss_name,
        "blind_type": None if blind is None else blind.type.value,
        "blind_requirement": None if blind is None else blind.requirement,
        "blind_reward": None if blind is None else blind.reward,
        "joker_count": len(state.jokers),
        "joker_slots": state.joker_slots,
        "consumable_count": len(state.consumables),
        "consumable_slots": state.consumable_slots,
        "status": frame.status.value,
        "owner": frame.owner.value,
        "tactical_actions": frame.info.get("tactical_actions"),
    }


def _shop_dict(
    run: HeadlessRunState,
    legal_actions: tuple[EnvAction, ...],
) -> dict[str, Any] | None:
    if not isinstance(run, HeadlessRunState):
        raise TypeError("strategic shop trace requires HeadlessRunState")
    state = run.public
    if state.phase != "SHOP":
        return None
    if not state.shop_active:
        raise PPOStrategicShopTraceError("SHOP boundary is not active")
    legal = tuple(_action_dict(action) for action in legal_actions)
    affordable = tuple(
        action for action in legal if action["alias"] in _PURCHASE_ALIASES
    )
    traced = tuple(
        action for action in legal if action["alias"] in _SHOP_TRACE_ALIASES
    )
    return {
        "money": state.money,
        "reroll_cost": run.reroll_cost,
        "reroll_cost_policy_observed": False,
        "owned": {
            "joker_count": len(state.jokers),
            "joker_slots": state.joker_slots,
            "consumable_count": len(state.consumables),
            "consumable_slots": state.consumable_slots,
            "vouchers": sorted(str(value) for value in state.vouchers),
        },
        "visible": {
            "jokers": [
                _shop_item_payload(item, "JOKER") for item in state.shop_jokers
            ],
            "consumables": [
                _shop_item_payload(item, "CONSUMABLE")
                for item in state.shop_consumables
            ],
            "boosters": [
                _shop_item_payload(item, "BOOSTER")
                for item in state.shop_boosters
            ],
            "vouchers": [
                _shop_item_payload(item, "VOUCHER")
                for item in state.shop_vouchers
            ],
        },
        "legal_actions": list(legal),
        "legal_purchase_end_reroll_actions": list(traced),
        "affordable_purchase_actions": list(affordable),
    }


class _TracingPPOHeadlessBackend(PPOHeadlessBackend):
    """Observe exact strategic boundaries without changing backend behavior."""

    def __init__(self, tactical_decision_engine: object):
        super().__init__(tactical_decision_engine)
        self.transitions: list[dict[str, Any]] = []

    def step(self, action: EnvAction):
        if self._frame is None:
            raise RuntimeError("strategic tracing backend has not been reset")
        legal_actions = self.legal_actions()
        before = {
            "frame": _frame_dict(self._frame),
            "shop": _shop_dict(self.run, legal_actions),
            "legal_actions": [_action_dict(value) for value in legal_actions],
        }
        result = super().step(action)
        self.transitions.append(
            {
                "before": before,
                "selected_action": _action_dict(action),
                "after": _frame_dict(result.frame),
            }
        )
        return result


def _decision_dict(
    decision: PPOCandidateDecision,
    transition: dict[str, Any],
) -> dict[str, Any]:
    if decision.action != EnvAction.from_alias(
        transition["selected_action"]["alias"],
        transition["selected_action"]["params"],
    ):
        raise PPOStrategicShopTraceError(
            "strategic trace action/transition drifted"
        )
    observation = {
        "schema_version": decision.observation.schema_version,
        "values": decision.observation.values,
    }
    digest = sha256(_canonical_bytes(observation)).hexdigest()
    value = {
        "decision_index": decision.decision_index,
        "before": transition["before"],
        "observation_schema_version": decision.observation.schema_version,
        "observation_sha256": digest,
        "action_mask_schema_version": decision.action_mask.schema_version,
        "action_mask": list(decision.action_mask.values),
        "probabilities": list(decision.probabilities),
        "value_estimate": decision.value_estimate,
        "selected_action_index": decision.action_index,
        "selected_action": _action_dict(decision.action),
        "after": transition["after"],
    }
    _validate_decision_dict(value)
    return value


def _validate_decision_dict(value: dict[str, Any]) -> None:
    try:
        mask = value["action_mask"]
        probabilities = value["probabilities"]
        selected_index = value["selected_action_index"]
        selected_action = value["selected_action"]
        estimate = value["value_estimate"]
        observation_schema = value["observation_schema_version"]
        observation_digest = value["observation_sha256"]
        action_schema = value["action_mask_schema_version"]
    except (KeyError, TypeError) as error:
        raise PPOStrategicShopTraceError(
            "strategic trace decision evidence is malformed"
        ) from error
    if (
        not isinstance(mask, list)
        or len(mask) != len(PUBLIC_ACTION_SCHEMA.slots)
        or any(type(allowed) is not bool for allowed in mask)
        or not isinstance(probabilities, list)
        or len(probabilities) != len(mask)
        or any(
            isinstance(probability, bool)
            or not isinstance(probability, (int, float))
            or not math.isfinite(float(probability))
            or probability < 0.0
            for probability in probabilities
        )
        or isinstance(estimate, bool)
        or not isinstance(estimate, (int, float))
        or not math.isfinite(float(estimate))
        or observation_schema != PUBLIC_OBSERVATION_VERSION
        or not isinstance(observation_digest, str)
        or len(observation_digest) != 64
        or observation_digest != observation_digest.lower()
        or any(
            character not in "0123456789abcdef"
            for character in observation_digest
        )
        or action_schema != PUBLIC_ACTION_VERSION
        or isinstance(selected_index, bool)
        or not isinstance(selected_index, int)
        or not 0 <= selected_index < len(mask)
        or not mask[selected_index]
        or any(
            probability != 0.0
            for probability, allowed in zip(probabilities, mask, strict=True)
            if not allowed
        )
        or not math.isclose(
            math.fsum(float(value) for value in probabilities),
            1.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
    ):
        raise PPOStrategicShopTraceError(
            "strategic trace decision mask/probabilities are invalid"
        )
    expected_action = _action_dict(action_from_index(selected_index))
    if selected_action != expected_action:
        raise PPOStrategicShopTraceError(
            "strategic trace indexed action drifted"
        )


def make_strategic_trace_environment(
    recorder: list[_TracingPPOHeadlessBackend],
) -> BalatroHeadlessEnvironment:
    if not isinstance(recorder, list) or recorder:
        raise PPOStrategicShopTraceError(
            "strategic trace backend recorder must be an empty list"
        )
    engine = make_ppo_tactical_decision_engine()
    if engine.search_schedule_mode != SEARCH_SCHEDULE_SELECTIVE:
        raise PPOStrategicShopTraceError(
            "strategic trace production schedule drifted"
        )
    backend = _TracingPPOHeadlessBackend(engine)
    recorder.append(backend)
    return BalatroHeadlessEnvironment(backend)


def _execute_trace_episode(
    campaign: CompletedPPOCampaign,
    identity: PPOCandidateIdentity,
    spec: FixedSeededEpisodeSpec,
) -> dict[str, Any]:
    backends: list[_TracingPPOHeadlessBackend] = []

    def factory(_stream_index):
        return make_strategic_trace_environment(backends)

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
    if (
        len(backends) != 1
        or len(backends[0].transitions) != len(evidence.decisions)
        or len(evidence.frames) != len(evidence.decisions) + 1
    ):
        raise PPOStrategicShopTraceError(
            "strategic trace transition evidence is incomplete"
        )
    decisions = [
        _decision_dict(decision, transition)
        for decision, transition in zip(
            evidence.decisions, backends[0].transitions, strict=True
        )
    ]
    metrics = derive_terminal_episode_metrics(
        status=evidence.result.status,
        action_count=evidence.result.action_count,
        frames=evidence.frames,
    )
    return {
        "episode_index": spec.episode_index,
        "game_seed": spec.game_seed,
        "policy_seed": evidence.result.policy_seed,
        "status": evidence.result.status.value,
        "action_count": evidence.result.action_count,
        "metrics": asdict(metrics),
        "first_blind_cleared": _first_blind_cleared(evidence.frames),
        "decisions": decisions,
    }


_WORKER_CAMPAIGN: CompletedPPOCampaign | None = None
_WORKER_IDENTITY: PPOCandidateIdentity | None = None


def _initialize_worker(campaign_directory: str) -> None:
    global _WORKER_CAMPAIGN, _WORKER_IDENTITY
    _WORKER_CAMPAIGN = load_completed_ppo_campaign(campaign_directory)
    _WORKER_IDENTITY = PPOCandidateIdentity.from_completed_campaign(
        _WORKER_CAMPAIGN
    )


def _worker(spec: FixedSeededEpisodeSpec) -> dict[str, Any]:
    if _WORKER_CAMPAIGN is None or _WORKER_IDENTITY is None:
        raise PPOStrategicShopTraceError("strategic trace worker is uninitialized")
    return _execute_trace_episode(_WORKER_CAMPAIGN, _WORKER_IDENTITY, spec)


def _load_reproduction(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        raw = source.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PPOStrategicShopTraceError(
            "strategic trace reproduction source is unreadable"
        ) from error
    if (
        sha256(raw).hexdigest() != CURRENT_REPRODUCTION_SHA256
        or not isinstance(value, dict)
        or _canonical_bytes(value) != raw
        or value.get("schema_version")
        != PPO_CURRENT_TACTICAL_REPRODUCTION_SCHEMA
        or value.get("decision") != "published-exact"
        or value.get("corpus_sha256") != FIXED_SEEDED_CORPUS_SHA256
        or not isinstance(value.get("episodes"), list)
    ):
        raise PPOStrategicShopTraceError(
            "strategic trace reproduction source drifted"
        )
    expected = tuple(
        (spec.episode_index, spec.game_seed, fixed_candidate_policy_seed(spec))
        for spec in FIXED_SEEDED_EPISODES
    )
    actual = tuple(
        (
            episode.get("episode_index"),
            episode.get("game_seed"),
            episode.get("policy_seed"),
        )
        for episode in value["episodes"]
        if isinstance(episode, dict)
    )
    if actual != expected:
        raise PPOStrategicShopTraceError(
            "strategic trace reproduction source order drifted"
        )
    return value


def summarize_strategic_shop_trace(
    episodes: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    expected = tuple(
        (spec.episode_index, spec.game_seed, fixed_candidate_policy_seed(spec))
        for spec in FIXED_SEEDED_EPISODES
    )
    actual = tuple(
        (
            episode.get("episode_index"),
            episode.get("game_seed"),
            episode.get("policy_seed"),
        )
        for episode in episodes
    )
    if actual != expected:
        raise PPOStrategicShopTraceError(
            "strategic trace episodes are incomplete or out of order"
        )
    phase_actions: Counter[tuple[str, str]] = Counter()
    shop_actions: Counter[str] = Counter()
    shop_decisions = 0
    end_shop_with_purchase = 0
    purchase_money_deltas: list[int] = []
    acquisition_families: Counter[str] = Counter()
    episodes_with_shop = 0
    shop_decisions_by_terminal_ante: Counter[int] = Counter()
    episode_shop_sequences: list[dict[str, Any]] = []
    for episode in episodes:
        saw_shop = False
        terminal_ante = int(episode["metrics"]["ante_reached"])
        terminal_progress = float(
            episode["metrics"]["terminal_requirement_progress"]
        )
        shop_sequence: list[dict[str, Any]] = []
        for expected_decision_index, decision in enumerate(episode["decisions"]):
            if decision.get("decision_index") != expected_decision_index:
                raise PPOStrategicShopTraceError(
                    "strategic trace decision order drifted"
                )
            _validate_decision_dict(decision)
            phase = decision["before"]["frame"]["phase"]
            alias = decision["selected_action"]["alias"]
            phase_actions[(phase, alias)] += 1
            if phase != "SHOP":
                continue
            saw_shop = True
            shop_decisions += 1
            shop_actions[alias] += 1
            shop_decisions_by_terminal_ante[terminal_ante] += 1
            shop = decision["before"]["shop"]
            if shop is None:
                raise PPOStrategicShopTraceError(
                    "SHOP decision is missing its exact shop snapshot"
                )
            if alias == "END_SHOP" and shop["affordable_purchase_actions"]:
                end_shop_with_purchase += 1
            before_money = int(decision["before"]["frame"]["money"])
            after_money = int(decision["after"]["money"])
            shop_sequence.append(
                {
                    "decision_index": decision["decision_index"],
                    "selected_action": decision["selected_action"],
                    "money_before": before_money,
                    "money_after": after_money,
                    "affordable_purchase_actions": shop[
                        "affordable_purchase_actions"
                    ],
                    "terminal_ante": terminal_ante,
                    "terminal_requirement_progress": terminal_progress,
                }
            )
            if alias in _PURCHASE_ALIASES:
                acquisition_families[alias] += 1
                purchase_money_deltas.append(after_money - before_money)
        episodes_with_shop += int(saw_shop)
        episode_shop_sequences.append(
            {
                "episode_index": episode["episode_index"],
                "game_seed": episode["game_seed"],
                "terminal_ante": terminal_ante,
                "terminal_requirement_progress": terminal_progress,
                "decisions": shop_sequence,
            }
        )
    return {
        "episode_count": len(episodes),
        "episodes_with_shop": episodes_with_shop,
        "strategic_decision_count": sum(
            len(episode["decisions"]) for episode in episodes
        ),
        "shop_decision_count": shop_decisions,
        "phase_action_frequencies": [
            {"phase": phase, "alias": alias, "count": count}
            for (phase, alias), count in sorted(phase_actions.items())
        ],
        "shop_action_frequencies": [
            {"alias": alias, "count": count}
            for alias, count in sorted(shop_actions.items())
        ],
        "end_shop_with_affordable_purchase_count": end_shop_with_purchase,
        "acquisition_family_frequencies": [
            {"alias": alias, "count": acquisition_families.get(alias, 0)}
            for alias in sorted(_PURCHASE_ALIASES)
        ],
        "purchase_count": len(purchase_money_deltas),
        "mean_purchase_money_delta": (
            fmean(purchase_money_deltas) if purchase_money_deltas else 0.0
        ),
        "shop_decisions_by_terminal_ante": [
            {"ante": ante, "count": count}
            for ante, count in sorted(shop_decisions_by_terminal_ante.items())
        ],
        "episode_shop_sequences": episode_shop_sequences,
    }


def run_strategic_shop_trace(
    campaign_directory: str | Path,
    promotion_directory: str | Path,
    reproduction_source: str | Path,
    output_path: str | Path,
    *,
    maximum_workers: int,
    episode_executor: Callable | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    destination = Path(output_path)
    if destination.exists():
        raise PPOStrategicShopTraceError("strategic shop trace output already exists")
    if not destination.parent.is_dir():
        raise PPOStrategicShopTraceError(
            "strategic shop trace output directory is missing"
        )
    if (
        isinstance(maximum_workers, bool)
        or not isinstance(maximum_workers, int)
        or not 1 <= maximum_workers <= 8
    ):
        raise PPOStrategicShopTraceError(
            "strategic shop trace workers must be from 1 through 8"
        )
    if episode_executor is not None and not callable(episode_executor):
        raise TypeError("strategic shop trace episode_executor must be callable")
    if progress_callback is not None and not callable(progress_callback):
        raise TypeError("strategic shop trace progress_callback must be callable")
    campaign_path = Path(campaign_directory)
    promotion_path = Path(promotion_directory)
    campaign = load_completed_ppo_campaign(campaign_path)
    identity = PPOCandidateIdentity.from_completed_campaign(campaign)
    reproduction = _load_reproduction(reproduction_source)
    expected_links = {
        "candidate_sha256": identity.sha256,
        "campaign_checkpoint_sha256": campaign.checkpoint_sha256,
        "campaign_progress_sha256": campaign.progress_sha256,
        "campaign_final_sha256": campaign.final_sha256,
        "promotion_final_sha256": sha256(
            (promotion_path / FINAL_ARTIFACT_NAME).read_bytes()
        ).hexdigest(),
    }
    if any(reproduction.get(key) != value for key, value in expected_links.items()):
        raise PPOStrategicShopTraceError(
            "strategic trace reproduction links drifted"
        )
    values: list[dict[str, Any]] = []

    def record(value: dict[str, Any]) -> None:
        values.append(value)
        if progress_callback is not None:
            progress_callback(len(values), len(FIXED_SEEDED_EPISODES))

    if episode_executor is None:
        context = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=maximum_workers,
            mp_context=context,
            initializer=_initialize_worker,
            initargs=(str(campaign_path),),
        ) as executor:
            for value in executor.map(_worker, FIXED_SEEDED_EPISODES):
                record(value)
    else:
        for spec in FIXED_SEEDED_EPISODES:
            record(episode_executor(campaign, identity, spec))

    for spec, expected, actual in zip(
        FIXED_SEEDED_EPISODES, reproduction["episodes"], values, strict=True
    ):
        baseline = expected["current_selective"]
        projection = {
            key: actual[key]
            for key in (
                "status",
                "action_count",
                "metrics",
                "first_blind_cleared",
            )
        }
        expected_projection = {
            key: baseline[key]
            for key in (
                "status",
                "action_count",
                "metrics",
                "first_blind_cleared",
            )
        }
        if (
            actual["episode_index"] != spec.episode_index
            or actual["game_seed"] != spec.game_seed
            or projection != expected_projection
        ):
            raise PPOStrategicShopTraceError(
                "strategic trace did not reproduce current production"
            )
    episodes = tuple(values)
    report = {
        "schema_version": PPO_STRATEGIC_SHOP_TRACE_SCHEMA,
        **expected_links,
        "current_reproduction_source_sha256": CURRENT_REPRODUCTION_SHA256,
        "corpus_version": FIXED_SEEDED_CORPUS_VERSION,
        "corpus_sha256": FIXED_SEEDED_CORPUS_SHA256,
        "episodes": list(episodes),
        "summary": summarize_strategic_shop_trace(episodes),
    }
    _atomic_write(destination, _canonical_bytes(report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-directory", required=True)
    parser.add_argument("--promotion-directory", required=True)
    parser.add_argument("--reproduction-source", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--maximum-workers", type=int, default=8)
    arguments = parser.parse_args(argv)

    def progress(completed: int, total: int) -> None:
        print(
            _canonical_bytes(
                {"completed_episodes": completed, "total_episodes": total}
            ).decode("utf-8"),
            flush=True,
        )

    report = run_strategic_shop_trace(
        arguments.campaign_directory,
        arguments.promotion_directory,
        arguments.reproduction_source,
        arguments.output_path,
        maximum_workers=arguments.maximum_workers,
        progress_callback=progress,
    )
    path = Path(arguments.output_path)
    print(
        _canonical_bytes(
            {
                "schema_version": report["schema_version"],
                "output_path": str(path),
                "report_sha256": sha256(path.read_bytes()).hexdigest(),
                "summary": report["summary"],
            }
        ).decode("utf-8")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
