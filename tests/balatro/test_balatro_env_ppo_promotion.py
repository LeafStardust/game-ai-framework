import json
from dataclasses import replace
from statistics import fmean

import pytest

from games.balatro.blinds.blind import create_small_blind
from games.balatro.env.evaluation_diagnostics import (
    aggregate_evaluation_diagnostics,
    derive_episode_diagnostics,
)
from games.balatro.env.ppo_candidate_evaluation import (
    PPOCandidateEpisodeEvidence,
    PPOCandidateEpisodeResult,
    PPOCandidateIdentity,
    fixed_candidate_policy_seed,
    run_fixed_ppo_candidate_evaluation,
    run_unseeded_ppo_candidate_evaluation,
    unseeded_candidate_policy_seed,
)
from games.balatro.env.ppo_campaign import PPO_CAMPAIGN_VERSION
from games.balatro.env.ppo_contract import PPO_TRAINING_CONTRACT
from games.balatro.env.ppo_promotion import (
    PPO_PROMOTION_REPORT_SCHEMA,
    PPOCandidateDiagnosticsReport,
    PPOPromotionError,
    aggregate_ppo_candidate_diagnostics,
    build_ppo_promotion_report,
    derive_ppo_candidate_diagnostics,
)
from games.balatro.env.promotion_contract import (
    B0_PROMOTION_CONTRACT_VERSION,
    ZERO_TOLERANCE_PATHOLOGIES,
)
from games.balatro.env.seeded_evaluation import (
    EVALUATED_BASELINE_VERSIONS,
    FIXED_SEEDED_CORPUS_SHA256,
    FixedSeededEpisodeResult,
    run_fixed_seeded_evaluation,
)
from games.balatro.env.state import EnvStateFrame, RunStatus, TurnOwner
from games.balatro.env.unseeded_evaluation import (
    UnseededEpisodeResult,
    create_unseeded_evaluation_manifest,
    run_unseeded_evaluation,
)
from games.balatro.env.action_encoding import PUBLIC_ACTION_VERSION
from games.balatro.env.observation_encoding import PUBLIC_OBSERVATION_VERSION
from games.balatro.env.ppo_candidate_evaluation import PPO_CANDIDATE_VERSION
from games.balatro.state import BalatroState


def _identity():
    return PPOCandidateIdentity(
        version=PPO_CANDIDATE_VERSION,
        campaign_version=PPO_CAMPAIGN_VERSION,
        promotion_contract_version=B0_PROMOTION_CONTRACT_VERSION,
        training_run_sha256="1" * 64,
        checkpoint_sha256="2" * 64,
        progress_sha256="3" * 64,
        final_sha256="4" * 64,
        policy_parameter_sha256="5" * 64,
        completed_batch_count=1024,
        optimizer_consumed_transitions=PPO_TRAINING_CONTRACT.total_environment_steps,
        observation_version=PUBLIC_OBSERVATION_VERSION,
        action_version=PUBLIC_ACTION_VERSION,
        deck="RED",
        stake="WHITE",
        mode="NORMAL",
    )


def _frames(game_seed, status, *, terminal_money=4, ante_loss=3):
    won = status is RunStatus.ANTE_8_WIN
    values = []
    for ante, money, score, phase, frame_status in (
        (1, 4, 0, "BLIND_SELECT", RunStatus.RUNNING),
        (8 if won else ante_loss, terminal_money, 120 if won else 80, "GAME_OVER", status),
    ):
        state = BalatroState()
        state.deck_name = "RED"
        state.stake_name = "WHITE"
        state.ante = ante
        state.money = money
        state.score = score
        state.phase = phase
        state.blind = create_small_blind(100)
        values.append(EnvStateFrame(
            state,
            status=frame_status,
            owner=TurnOwner.TERMINAL if frame_status.terminal else TurnOwner.AGENT,
            info={"game_seed": game_seed},
        ))
    return tuple(values)


def _candidate_fixed(clear_count=30, *, terminal_money=4):
    identity = _identity()
    source = run_fixed_ppo_candidate_evaluation(
        identity,
        lambda actual, spec, seed: PPOCandidateEpisodeResult.completed(
            actual,
            evidence_kind="FIXED_SEEDED",
            evidence_sha256=FIXED_SEEDED_CORPUS_SHA256,
            episode_index=spec.episode_index,
            game_seed=spec.game_seed,
            policy_seed=seed,
            status=RunStatus.ANTE_8_WIN if spec.episode_index < clear_count else RunStatus.LOSS,
            action_count=1,
        ),
    )
    diagnostics = tuple(
        derive_ppo_candidate_diagnostics(
            identity,
            PPOCandidateEpisodeEvidence(
                result,
                _frames(result.game_seed, result.status, terminal_money=terminal_money),
            ),
        )
        for result in source.episodes
    )
    return aggregate_ppo_candidate_diagnostics(source, diagnostics)


def _baseline_fixed(clear_counts=(20, 22), *, terminal_money=4):
    counts = dict(zip(EVALUATED_BASELINE_VERSIONS, clear_counts, strict=True))
    source = run_fixed_seeded_evaluation(
        lambda baseline, spec, seed: FixedSeededEpisodeResult.completed(
            baseline_version=baseline,
            episode_index=spec.episode_index,
            game_seed=spec.game_seed,
            policy_seed=seed,
            status=RunStatus.ANTE_8_WIN if spec.episode_index < counts[baseline] else RunStatus.LOSS,
            action_count=1,
        )
    )
    diagnostics = tuple(
        derive_episode_diagnostics(
            result,
            _frames(result.game_seed, result.status, terminal_money=terminal_money),
        )
        for result in source.episodes
    )
    return aggregate_evaluation_diagnostics(source, diagnostics)


def _candidate_unseeded(byte, clear_count=24, *, terminal_money=4):
    identity = _identity()
    manifest = create_unseeded_evaluation_manifest(lambda size: bytes([byte]) * size)
    source = run_unseeded_ppo_candidate_evaluation(
        identity,
        manifest,
        lambda actual, spec, seed: PPOCandidateEpisodeResult.completed(
            actual,
            evidence_kind="UNSEEDED",
            evidence_sha256=manifest.manifest_sha256,
            episode_index=spec.episode_index,
            game_seed=spec.game_seed,
            policy_seed=seed,
            status=RunStatus.ANTE_8_WIN if spec.episode_index < clear_count else RunStatus.LOSS,
            action_count=1,
        ),
    )
    diagnostics = tuple(
        derive_ppo_candidate_diagnostics(
            identity,
            PPOCandidateEpisodeEvidence(
                result,
                _frames(result.game_seed, result.status, terminal_money=terminal_money),
            ),
        )
        for result in source.episodes
    )
    return aggregate_ppo_candidate_diagnostics(source, diagnostics), manifest


def _baseline_unseeded(manifest, clear_counts=(8, 10), *, terminal_money=4):
    counts = dict(zip(EVALUATED_BASELINE_VERSIONS, clear_counts, strict=True))
    source = run_unseeded_evaluation(
        manifest,
        lambda baseline, spec, seed: UnseededEpisodeResult.completed(
            manifest,
            baseline_version=baseline,
            episode_index=spec.episode_index,
            game_seed=spec.game_seed,
            policy_seed=seed,
            status=RunStatus.ANTE_8_WIN if spec.episode_index < counts[baseline] else RunStatus.LOSS,
            action_count=1,
        ),
    )
    diagnostics = tuple(
        derive_episode_diagnostics(
            result,
            _frames(result.game_seed, result.status, terminal_money=terminal_money),
        )
        for result in source.episodes
    )
    return aggregate_evaluation_diagnostics(source, diagnostics)


def _evidence(*, fixed_candidate_clears=30, unseeded_candidate_clears=24,
              fixed_baseline_clears=(20, 22), unseeded_baseline_clears=(8, 10),
              candidate_money=4, baseline_money=4):
    candidates = []
    baselines = []
    for byte in (11, 12, 13, 14):
        candidate, manifest = _candidate_unseeded(
            byte, unseeded_candidate_clears, terminal_money=candidate_money
        )
        candidates.append(candidate)
        baselines.append(_baseline_unseeded(
            manifest, unseeded_baseline_clears, terminal_money=baseline_money
        ))
    return (
        _candidate_fixed(fixed_candidate_clears, terminal_money=candidate_money),
        _baseline_fixed(fixed_baseline_clears, terminal_money=baseline_money),
        tuple(candidates),
        tuple(baselines),
    )


def _zero_pathologies():
    return {name: 0 for name in ZERO_TOLERANCE_PATHOLOGIES}


def _with_secondary_regression(report, metric):
    episodes = []
    for item in report.episodes:
        values = item.metrics
        if metric == "mean_ante_reached" and item.status is RunStatus.LOSS:
            values = replace(values, ante_reached=1)
        elif metric == "mean_terminal_requirement_progress" and item.status is RunStatus.LOSS:
            values = replace(
                values,
                terminal_blind_score=60.0,
                terminal_chip_margin=-40.0,
                terminal_requirement_progress=0.6,
            )
        elif metric == "mean_minimum_money":
            values = replace(values, minimum_money=1)
        elif metric == "mean_terminal_money":
            values = replace(values, minimum_money=1, terminal_money=1)
        episodes.append(replace(item, metrics=values))
    episodes = tuple(episodes)
    summary = replace(
        report.summary,
        mean_ante_reached=fmean(item.metrics.ante_reached for item in episodes),
        mean_terminal_requirement_progress=fmean(
            item.metrics.terminal_requirement_progress for item in episodes
        ),
        mean_minimum_money=fmean(item.metrics.minimum_money for item in episodes),
        mean_terminal_money=fmean(item.metrics.terminal_money for item in episodes),
    )
    return replace(report, episodes=episodes, summary=summary)


def test_env_ppo_candidate_diagnostics_bind_exact_trace_and_source():
    report = _candidate_fixed()

    assert isinstance(report, PPOCandidateDiagnosticsReport)
    assert report.episode_count == 64
    assert report.summary.ante_8_clears == 30
    assert report.episodes[0].metrics.frame_count == 2
    assert json.loads(report.to_json())["identity"] == _identity().as_dict()


def test_env_ppo_promotion_report_passes_all_frozen_gates_and_serializes():
    report = build_ppo_promotion_report(*_evidence(), pathology_counts=_zero_pathologies())

    assert report.schema_version == PPO_PROMOTION_REPORT_SCHEMA
    assert report.promoted is True
    assert all(gate.passed for gate in report.gates)
    assert len(report.unseeded_candidate_source_sha256s) == 4
    assert report.to_json() == report.to_json()
    assert json.loads(report.to_json())["promoted"] is True


@pytest.mark.parametrize(
    ("changes", "gate_prefix"),
    [
        ({"fixed_candidate_clears": 10}, "fixed_clear_nonregression:"),
        ({"unseeded_candidate_clears": 10}, "unseeded_minimum_candidate_clear_rate"),
        (
            {"unseeded_candidate_clears": 14, "unseeded_baseline_clears": (12, 12)},
            "unseeded_clear_rate_delta:",
        ),
        (
            {"unseeded_candidate_clears": 16, "unseeded_baseline_clears": (12, 12)},
            "unseeded_wilson_superiority:",
        ),
    ],
)
def test_env_ppo_promotion_each_gate_category_fails_closed(changes, gate_prefix):
    report = build_ppo_promotion_report(
        *_evidence(**changes), pathology_counts=_zero_pathologies()
    )

    assert report.promoted is False
    assert any(not gate.passed and gate.name.startswith(gate_prefix) for gate in report.gates)


@pytest.mark.parametrize(
    "metric",
    [
        "mean_ante_reached",
        "mean_terminal_requirement_progress",
        "mean_minimum_money",
        "mean_terminal_money",
    ],
)
def test_env_ppo_promotion_each_secondary_threshold_fails_closed(metric):
    fixed_candidate, fixed_baselines, candidates, baselines = _evidence()
    candidates = tuple(_with_secondary_regression(item, metric) for item in candidates)
    report = build_ppo_promotion_report(
        _with_secondary_regression(fixed_candidate, metric),
        fixed_baselines,
        candidates,
        baselines,
        pathology_counts=_zero_pathologies(),
    )

    assert report.promoted is False
    assert any(
        not gate.passed and gate.name.startswith("secondary:") and gate.name.endswith(metric)
        for gate in report.gates
    )


def test_env_ppo_promotion_pathology_gate_has_zero_tolerance():
    counts = _zero_pathologies()
    counts["illegal_action"] = 1
    report = build_ppo_promotion_report(*_evidence(), pathology_counts=counts)

    assert report.promoted is False
    assert next(gate for gate in report.gates if gate.name == "pathology:illegal_action").passed is False


def test_env_ppo_promotion_rejects_missing_reordered_and_provenance_drift():
    fixed_candidate, fixed_baselines, candidates, baselines = _evidence()
    with pytest.raises(PPOPromotionError, match="exactly four"):
        build_ppo_promotion_report(
            fixed_candidate, fixed_baselines, candidates[:-1], baselines[:-1],
            pathology_counts=_zero_pathologies(),
        )
    with pytest.raises(PPOPromotionError, match="manifest provenance"):
        build_ppo_promotion_report(
            fixed_candidate, fixed_baselines, candidates, tuple(reversed(baselines)),
            pathology_counts=_zero_pathologies(),
        )
    incomplete = _zero_pathologies()
    incomplete.pop("schema_mismatch")
    with pytest.raises(PPOPromotionError, match="audit is incomplete"):
        build_ppo_promotion_report(
            fixed_candidate, fixed_baselines, candidates, baselines,
            pathology_counts=incomplete,
        )


def test_env_ppo_promotion_report_rejects_decision_tampering():
    report = build_ppo_promotion_report(*_evidence(), pathology_counts=_zero_pathologies())

    with pytest.raises(PPOPromotionError, match="contradicts"):
        replace(report, promoted=False)
    with pytest.raises(PPOPromotionError, match="gates are invalid"):
        replace(report, gates=tuple(reversed(report.gates)))
    first = report.gates[0]
    with pytest.raises(PPOPromotionError, match="contradicts its values"):
        replace(first, passed=not first.passed)
