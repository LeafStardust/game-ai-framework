import json
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace

import pytest

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.episode_backend import PPOHeadlessBackend
from games.balatro.env.ppo_campaign import CompletedPPOCampaign
from games.balatro.env.ppo_candidate_evaluation import (
    FIXED_EVIDENCE_KIND,
    PPOCandidateEpisodeResult,
    PPOCandidateIdentity,
    fixed_candidate_policy_seed,
    run_fixed_ppo_candidate_evaluation,
)
from games.balatro.env.ppo_candidate_trace import (
    PPO_CANDIDATE_TRACE_SCHEMA,
    FixedCandidateTraceReport,
    PPOCandidateTraceError,
    build_fixed_candidate_trace_report,
    load_published_fixed_sources,
    select_fixed_trace_episode_indices,
)
from games.balatro.env.ppo_contract import (
    PPO_POLICY_OUTPUT_SCHEMA,
    PPO_TRAINING_CONTRACT,
    PPOPolicyOutput,
    PPOTrainingRun,
)
from games.balatro.env.ppo_promotion_evaluation import PPO_PROMOTION_PUBLICATION_VERSION
from games.balatro.env.seeded_evaluation import (
    EVALUATED_BASELINE_VERSIONS,
    FIXED_SEEDED_CORPUS_SHA256,
    FixedSeededEpisodeResult,
    run_fixed_seeded_evaluation,
)
from games.balatro.env.state import RunStatus


class _OneCardTacticalPolicy:
    def decide(self, state):
        return SimpleNamespace(action=BalatroAction(PLAY_CARDS, cards=[state.hand[0]]))


class _SelectBlindModel:
    parameter_sha256 = "5" * 64

    def infer(self, observation, action_mask):
        probabilities = [0.0] * PPO_TRAINING_CONTRACT.action_size
        index = next(index for index, allowed in enumerate(action_mask.values) if allowed)
        probabilities[index] = 1.0
        return PPOPolicyOutput(
            schema_version=PPO_POLICY_OUTPUT_SCHEMA,
            observation_version=PPO_TRAINING_CONTRACT.observation_version,
            action_version=PPO_TRAINING_CONTRACT.action_version,
            probabilities=tuple(probabilities),
            value_estimate=-0.25,
        )


def _campaign():
    session = SimpleNamespace(
        learner=SimpleNamespace(completed_batch_count=1024, model=_SelectBlindModel()),
        optimizer_consumed_transitions=PPO_TRAINING_CONTRACT.total_environment_steps,
    )
    return CompletedPPOCampaign(
        training_run=PPOTrainingRun.from_seed("CANDIDATE"),
        session=session,
        checkpoint_sha256="2" * 64,
        progress_sha256="3" * 64,
        final_sha256="4" * 64,
        policy_parameter_sha256="5" * 64,
    )


def _environment(stream):
    assert stream == 0
    return BalatroHeadlessEnvironment(PPOHeadlessBackend(_OneCardTacticalPolicy()))


def _symbolic_first(state, actions):
    return actions[0]


def _sources(*, action_counts=None):
    campaign = _campaign()
    identity = PPOCandidateIdentity.from_completed_campaign(campaign)
    counts = action_counts or {}
    candidate = run_fixed_ppo_candidate_evaluation(
        identity,
        lambda actual, spec, seed: PPOCandidateEpisodeResult.completed(
            actual,
            evidence_kind=FIXED_EVIDENCE_KIND,
            evidence_sha256=FIXED_SEEDED_CORPUS_SHA256,
            episode_index=spec.episode_index,
            game_seed=spec.game_seed,
            policy_seed=seed,
            status=RunStatus.LOSS,
            action_count=counts.get(spec.episode_index, 1),
        ),
    )
    baselines = run_fixed_seeded_evaluation(
        lambda baseline, spec, seed: FixedSeededEpisodeResult.completed(
            baseline_version=baseline,
            episode_index=spec.episode_index,
            game_seed=spec.game_seed,
            policy_seed=seed,
            status=RunStatus.LOSS,
            action_count=1,
        )
    )
    return campaign, candidate, baselines


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def test_env_ppo_candidate_trace_replays_published_candidate_and_both_baselines():
    campaign, candidate, baselines = _sources()
    report = build_fixed_candidate_trace_report(
        campaign,
        candidate,
        baselines,
        evaluation_sha256="6" * 64,
        promotion_report_sha256="7" * 64,
        fixed_candidate_source_sha256="8" * 64,
        fixed_baseline_source_sha256="9" * 64,
        episode_indices=(0, 1),
        environment_factory=_environment,
        symbolic_decider=_symbolic_first,
    )

    assert isinstance(report, FixedCandidateTraceReport)
    assert report.schema_version == PPO_CANDIDATE_TRACE_SCHEMA
    assert report.episode_indices == (0, 1)
    assert report.selected_action_counts == (("SELECT_BLIND", 2),)
    assert all(len(episode.decisions) == 1 for episode in report.episodes)
    assert all(
        tuple(item.baseline_version for item in episode.baselines)
        == EVALUATED_BASELINE_VERSIONS
        for episode in report.episodes
    )
    assert all(
        tuple(item.expected_action_count for item in episode.baselines) == (1, 1)
        for episode in report.episodes
    )
    assert report.to_json() == report.to_json()
    assert json.loads(report.to_json())["selected_action_counts"] == {"SELECT_BLIND": 2}


def test_env_ppo_candidate_trace_pins_two_earliest_losses_and_longest_trajectory():
    _, candidate, _ = _sources(action_counts={5: 1, 15: 1, 12: 17, **{
        index: 3 for index in range(64) if index not in (5, 12, 15)
    }})

    assert select_fixed_trace_episode_indices(candidate) == (5, 15, 12)


def test_env_ppo_candidate_trace_rejects_probability_and_order_tampering():
    campaign, candidate, baselines = _sources()
    report = build_fixed_candidate_trace_report(
        campaign,
        candidate,
        baselines,
        evaluation_sha256="6" * 64,
        promotion_report_sha256="7" * 64,
        fixed_candidate_source_sha256="8" * 64,
        fixed_baseline_source_sha256="9" * 64,
        episode_indices=(0,),
        environment_factory=_environment,
        symbolic_decider=_symbolic_first,
    )
    decision = report.episodes[0].decisions[0]
    probabilities = list(decision.probabilities)
    probabilities[decision.selected_action_index] = 0.5

    with pytest.raises(PPOCandidateTraceError, match="probabilities"):
        replace(decision, probabilities=tuple(probabilities))
    with pytest.raises(PPOCandidateTraceError, match="ordering"):
        replace(report, episode_indices=(1,))


def test_env_ppo_candidate_trace_loads_only_digest_bound_published_sources(tmp_path):
    campaign, candidate, baselines = _sources()
    candidate_bytes = candidate.to_json().encode()
    baseline_bytes = baselines.to_json().encode()
    promotion_bytes = _canonical({"promoted": False})
    artifacts = {
        "fixed-candidate.json": sha256(candidate_bytes).hexdigest(),
        "fixed-baselines.json": sha256(baseline_bytes).hexdigest(),
        "promotion.json": sha256(promotion_bytes).hexdigest(),
    }
    final = {
        "version": PPO_PROMOTION_PUBLICATION_VERSION,
        "evaluation_sha256": "6" * 64,
        "candidate_sha256": candidate.identity.sha256,
        "promotion_report_sha256": artifacts["promotion.json"],
        "promoted": False,
        "artifacts": artifacts,
    }
    (tmp_path / "fixed-candidate.json").write_bytes(candidate_bytes)
    (tmp_path / "fixed-baselines.json").write_bytes(baseline_bytes)
    (tmp_path / "promotion.json").write_bytes(promotion_bytes)
    (tmp_path / "final.json").write_bytes(_canonical(final))

    loaded_final, loaded_candidate, loaded_baselines = load_published_fixed_sources(
        campaign, tmp_path
    )

    assert loaded_final == final
    assert loaded_candidate == candidate
    assert loaded_baselines == baselines

    (tmp_path / "fixed-candidate.json").write_bytes(candidate_bytes + b"\n")
    with pytest.raises(PPOCandidateTraceError, match="digest mismatch"):
        load_published_fixed_sources(campaign, tmp_path)
