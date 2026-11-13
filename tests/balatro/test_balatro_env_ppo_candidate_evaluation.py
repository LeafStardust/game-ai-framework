import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from games.balatro.env.action_encoding import legal_action_mask
from games.balatro.env.actions import EnvAction
from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.episode_backend import PPOHeadlessBackend
from games.balatro.env.observation_encoding import EncodedPublicObservation
from games.balatro.env.ppo_campaign import CompletedPPOCampaign
from games.balatro.env.ppo_candidate_evaluation import (
    FIXED_EVIDENCE_KIND,
    PPO_CANDIDATE_EPISODE_SCHEMA,
    PPO_CANDIDATE_FIXED_REPORT_SCHEMA,
    PPO_CANDIDATE_UNSEEDED_REPORT_SCHEMA,
    UNSEEDED_EVIDENCE_KIND,
    PPOCandidateEpisodeResult,
    PPOCandidateEpisodeEvidence,
    PPOCandidateEvaluationError,
    PPOCandidateFixedReport,
    PPOCandidateIdentity,
    fixed_candidate_policy_seed,
    execute_ppo_candidate_episode,
    run_fixed_ppo_candidate_evaluation,
    run_unseeded_ppo_candidate_evaluation,
    select_ppo_candidate_action,
    unseeded_candidate_policy_seed,
)
from games.balatro.env.ppo_contract import (
    PPO_POLICY_OUTPUT_SCHEMA,
    PPO_TRAINING_CONTRACT,
    PPOPolicyOutput,
    PPOTrainingRun,
)
from games.balatro.env.seeded_evaluation import (
    FIXED_SEEDED_CORPUS_SHA256,
    FIXED_SEEDED_EPISODES,
)
from games.balatro.env.state import RunStatus
from games.balatro.env.unseeded_evaluation import create_unseeded_evaluation_manifest
from games.balatro.env.ppo_promotion import execute_fixed_ppo_candidate_evaluation
from games.balatro.actions import PLAY_CARDS, BalatroAction


def _identity():
    run = PPOTrainingRun.from_seed("CANDIDATE")
    session = SimpleNamespace(
        learner=SimpleNamespace(completed_batch_count=1024),
        optimizer_consumed_transitions=2_097_152,
    )
    campaign = CompletedPPOCampaign(
        training_run=run,
        session=session,
        checkpoint_sha256="1" * 64,
        progress_sha256="2" * 64,
        final_sha256="3" * 64,
        policy_parameter_sha256="4" * 64,
    )
    return PPOCandidateIdentity.from_completed_campaign(campaign)


class _OneCardTacticalPolicy:
    def decide(self, state):
        return SimpleNamespace(action=BalatroAction(PLAY_CARDS, cards=[state.hand[0]]))


class _SelectBlindModel:
    def __init__(self, identity):
        self.parameter_sha256 = identity.policy_parameter_sha256

    def infer(self, observation, action_mask):
        probabilities = [0.0] * PPO_TRAINING_CONTRACT.action_size
        select_index = next(
            index
            for index, action in enumerate(action_mask.values)
            if action
        )
        probabilities[select_index] = 1.0
        return PPOPolicyOutput(
            schema_version=PPO_POLICY_OUTPUT_SCHEMA,
            observation_version=PPO_TRAINING_CONTRACT.observation_version,
            action_version=PPO_TRAINING_CONTRACT.action_version,
            probabilities=tuple(probabilities),
            value_estimate=0.0,
        )


def _campaign_with_model(identity, model):
    run = PPOTrainingRun.from_seed("CANDIDATE")
    session = SimpleNamespace(
        learner=SimpleNamespace(completed_batch_count=1024, model=model),
        optimizer_consumed_transitions=2_097_152,
    )
    return CompletedPPOCampaign(
        training_run=run,
        session=session,
        checkpoint_sha256=identity.checkpoint_sha256,
        progress_sha256=identity.progress_sha256,
        final_sha256=identity.final_sha256,
        policy_parameter_sha256=identity.policy_parameter_sha256,
    )


def _manifest(byte=7):
    return create_unseeded_evaluation_manifest(lambda size: bytes([byte]) * size)


def _fixed_result(identity, spec, policy_seed):
    return PPOCandidateEpisodeResult.completed(
        identity,
        evidence_kind=FIXED_EVIDENCE_KIND,
        evidence_sha256=FIXED_SEEDED_CORPUS_SHA256,
        episode_index=spec.episode_index,
        game_seed=spec.game_seed,
        policy_seed=policy_seed,
        status=RunStatus.LOSS,
        action_count=spec.episode_index,
    )


def _unseeded_result(manifest, identity, spec, policy_seed):
    return PPOCandidateEpisodeResult.completed(
        identity,
        evidence_kind=UNSEEDED_EVIDENCE_KIND,
        evidence_sha256=manifest.manifest_sha256,
        episode_index=spec.episode_index,
        game_seed=spec.game_seed,
        policy_seed=policy_seed,
        status=RunStatus.LOSS,
        action_count=spec.episode_index,
    )


def test_env_ppo_candidate_identity_binds_completed_campaign_and_is_canonical():
    identity = _identity()
    payload = json.loads(identity.to_json())

    assert identity.completed_batch_count == 1024
    assert identity.optimizer_consumed_transitions == 2_097_152
    assert identity.policy_parameter_sha256 == "4" * 64
    assert payload == identity.as_dict()
    assert len(identity.sha256) == 64
    assert identity.sha256 == _identity().sha256


@pytest.mark.parametrize(
    "change",
    (
        {"checkpoint_sha256": "x" * 64},
        {"completed_batch_count": 1023},
        {"optimizer_consumed_transitions": 2_095_104},
        {"observation_version": "old"},
        {"deck": "BLUE"},
    ),
)
def test_env_ppo_candidate_identity_fails_closed_on_drift(change):
    with pytest.raises(PPOCandidateEvaluationError):
        replace(_identity(), **change)


def test_env_ppo_candidate_fixed_schedule_is_complete_paired_and_pinned():
    identity = _identity()
    calls = []

    def execute(actual_identity, spec, policy_seed):
        calls.append((actual_identity.sha256, spec.episode_index, spec.game_seed, policy_seed))
        return _fixed_result(actual_identity, spec, policy_seed)

    report = run_fixed_ppo_candidate_evaluation(identity, execute)

    assert report.schema_version == PPO_CANDIDATE_FIXED_REPORT_SCHEMA
    assert report.episode_count == 64
    assert tuple(item[2] for item in calls) == tuple(
        spec.game_seed for spec in FIXED_SEEDED_EPISODES
    )
    assert tuple(item[3] for item in calls) == tuple(
        fixed_candidate_policy_seed(spec) for spec in FIXED_SEEDED_EPISODES
    )
    assert report.episodes[0].schema_version == PPO_CANDIDATE_EPISODE_SCHEMA
    assert json.loads(report.to_json())["identity"] == identity.as_dict()


def test_env_ppo_candidate_unseeded_schedule_binds_manifest_and_order():
    identity = _identity()
    manifest = _manifest()
    report = run_unseeded_ppo_candidate_evaluation(
        identity,
        manifest,
        lambda actual_identity, spec, policy_seed: _unseeded_result(
            manifest, actual_identity, spec, policy_seed
        ),
    )

    assert report.schema_version == PPO_CANDIDATE_UNSEEDED_REPORT_SCHEMA
    assert report.episode_count == 64
    assert tuple(item.game_seed for item in report.episodes) == tuple(
        spec.game_seed for spec in manifest.episodes
    )
    assert tuple(item.policy_seed for item in report.episodes) == tuple(
        unseeded_candidate_policy_seed(manifest, spec)
        for spec in manifest.episodes
    )
    assert json.loads(report.to_json())["manifest"] == manifest.as_dict()


def test_env_ppo_candidate_reports_reject_missing_reordered_and_drifted_evidence():
    identity = _identity()
    fixed = run_fixed_ppo_candidate_evaluation(identity, _fixed_result)
    manifest = _manifest()
    unseeded = run_unseeded_ppo_candidate_evaluation(
        identity,
        manifest,
        lambda actual_identity, spec, policy_seed: _unseeded_result(
            manifest, actual_identity, spec, policy_seed
        ),
    )

    for episodes in (fixed.episodes[:-1], tuple(reversed(fixed.episodes))):
        with pytest.raises(PPOCandidateEvaluationError, match="incomplete or out of order"):
            replace(fixed, episodes=episodes)
    with pytest.raises(PPOCandidateEvaluationError, match="incomplete or out of order"):
        replace(
            unseeded,
            episodes=(replace(unseeded.episodes[0], game_seed="DRIFT"),)
            + unseeded.episodes[1:],
        )


def test_env_ppo_candidate_action_sampling_is_deterministic_masked_and_isolated():
    identity = _identity()
    observation = EncodedPublicObservation(
        PPO_TRAINING_CONTRACT.observation_version,
        (0.0,) * PPO_TRAINING_CONTRACT.observation_size,
    )
    actions = (EnvAction.from_alias("SELECT_BLIND"), EnvAction.from_alias("SKIP_BLIND"))
    mask = legal_action_mask(actions)
    probabilities = tuple(
        0.5 if allowed else 0.0 for allowed in mask.values
    )
    output = PPOPolicyOutput(
        schema_version=PPO_POLICY_OUTPUT_SCHEMA,
        observation_version=PPO_TRAINING_CONTRACT.observation_version,
        action_version=PPO_TRAINING_CONTRACT.action_version,
        probabilities=probabilities,
        value_estimate=0.25,
    )
    seed = fixed_candidate_policy_seed(FIXED_SEEDED_EPISODES[0])

    first = select_ppo_candidate_action(
        identity,
        policy_seed=seed,
        decision_index=0,
        observation=observation,
        legal_actions=actions,
        policy_output=output,
    )
    second = select_ppo_candidate_action(
        identity,
        policy_seed=seed,
        decision_index=0,
        observation=observation,
        legal_actions=actions,
        policy_output=output,
    )

    assert first == second
    assert first.action in actions
    assert first.action_mask == mask
    assert first.candidate_sha256 == identity.sha256
    assert first.policy_seed != FIXED_SEEDED_EPISODES[0].random_policy_seed


def test_env_ppo_candidate_executor_and_terminal_contract_fail_closed():
    identity = _identity()
    spec = FIXED_SEEDED_EPISODES[0]
    seed = fixed_candidate_policy_seed(spec)
    result = _fixed_result(identity, spec, seed)

    with pytest.raises(TypeError, match="executor"):
        run_fixed_ppo_candidate_evaluation(identity, None)
    with pytest.raises(TypeError, match="must return"):
        run_fixed_ppo_candidate_evaluation(identity, lambda *args: None)
    with pytest.raises(PPOCandidateEvaluationError, match="terminal"):
        replace(result, status=RunStatus.RUNNING)
    with pytest.raises(PPOCandidateEvaluationError, match="policy seed"):
        replace(result, policy_seed="BAD")
    with pytest.raises(PPOCandidateEvaluationError, match="fixed episode spec"):
        fixed_candidate_policy_seed(replace(spec, game_seed="DRIFT"))


def test_env_ppo_candidate_executor_runs_exact_reset_to_terminal_trace():
    identity = _identity()
    model = _SelectBlindModel(identity)
    campaign = _campaign_with_model(identity, model)
    spec = FIXED_SEEDED_EPISODES[0]
    policy_seed = fixed_candidate_policy_seed(spec)

    evidence = execute_ppo_candidate_episode(
        campaign,
        identity,
        evidence_kind=FIXED_EVIDENCE_KIND,
        evidence_sha256=FIXED_SEEDED_CORPUS_SHA256,
        episode_index=spec.episode_index,
        game_seed=spec.game_seed,
        policy_seed=policy_seed,
        environment_factory=lambda stream: BalatroHeadlessEnvironment(
            PPOHeadlessBackend(_OneCardTacticalPolicy())
        ),
    )

    assert isinstance(evidence, PPOCandidateEpisodeEvidence)
    assert evidence.result.status is RunStatus.LOSS
    assert evidence.result.action_count == 1
    assert len(evidence.frames) == 2
    assert evidence.frames[0].state.phase == "BLIND_SELECT"
    assert evidence.frames[-1].state.phase == "GAME_OVER"
    assert all(frame.info["game_seed"] == spec.game_seed for frame in evidence.frames)


def test_env_ppo_candidate_executor_rejects_identity_model_and_backend_drift():
    identity = _identity()
    model = _SelectBlindModel(identity)
    campaign = _campaign_with_model(identity, model)
    spec = FIXED_SEEDED_EPISODES[0]
    kwargs = dict(
        evidence_kind=FIXED_EVIDENCE_KIND,
        evidence_sha256=FIXED_SEEDED_CORPUS_SHA256,
        episode_index=spec.episode_index,
        game_seed=spec.game_seed,
        policy_seed=fixed_candidate_policy_seed(spec),
    )

    with pytest.raises(PPOCandidateEvaluationError, match="identity does not match"):
        execute_ppo_candidate_episode(
            campaign,
            replace(identity, checkpoint_sha256="5" * 64),
            environment_factory=lambda stream: BalatroHeadlessEnvironment(
                PPOHeadlessBackend(_OneCardTacticalPolicy())
            ),
            **kwargs,
        )

    model.parameter_sha256 = "6" * 64
    with pytest.raises(PPOCandidateEvaluationError, match="model parameter identity"):
        execute_ppo_candidate_episode(
            campaign,
            identity,
            environment_factory=lambda stream: BalatroHeadlessEnvironment(
                PPOHeadlessBackend(_OneCardTacticalPolicy())
            ),
            **kwargs,
        )

    model.parameter_sha256 = identity.policy_parameter_sha256
    with pytest.raises(TypeError, match="must return BalatroHeadlessEnvironment"):
        execute_ppo_candidate_episode(
            campaign,
            identity,
            environment_factory=lambda stream: object(),
            **kwargs,
        )

    class _DriftedEnvironment(BalatroHeadlessEnvironment):
        def reset(self, *, seed):
            value = super().reset(seed=seed)
            self._frame.info["backend_schema"] = "DRIFT"
            return value

    with pytest.raises(PPOCandidateEvaluationError, match="backend schema"):
        execute_ppo_candidate_episode(
            campaign,
            identity,
            environment_factory=lambda stream: _DriftedEnvironment(
                PPOHeadlessBackend(_OneCardTacticalPolicy())
            ),
            **kwargs,
        )


def test_env_ppo_candidate_executor_rejects_truncation(monkeypatch):
    identity = _identity()
    model = _SelectBlindModel(identity)
    campaign = _campaign_with_model(identity, model)
    spec = FIXED_SEEDED_EPISODES[0]
    real_step = BalatroHeadlessEnvironment.step

    def truncated_step(environment, action):
        observation, reward, terminated, _, info = real_step(environment, action)
        return observation, reward, terminated, True, info

    monkeypatch.setattr(BalatroHeadlessEnvironment, "step", truncated_step)
    with pytest.raises(PPOCandidateEvaluationError, match="truncated"):
        execute_ppo_candidate_episode(
            campaign,
            identity,
            evidence_kind=FIXED_EVIDENCE_KIND,
            evidence_sha256=FIXED_SEEDED_CORPUS_SHA256,
            episode_index=spec.episode_index,
            game_seed=spec.game_seed,
            policy_seed=fixed_candidate_policy_seed(spec),
            environment_factory=lambda stream: BalatroHeadlessEnvironment(
                PPOHeadlessBackend(_OneCardTacticalPolicy())
            ),
        )


def test_env_ppo_candidate_fixed_executor_binds_all_results_and_diagnostics():
    identity = _identity()
    campaign = _campaign_with_model(identity, _SelectBlindModel(identity))

    bundle = execute_fixed_ppo_candidate_evaluation(
        campaign,
        environment_factory=lambda stream: BalatroHeadlessEnvironment(
            PPOHeadlessBackend(_OneCardTacticalPolicy())
        ),
    )

    assert bundle.source.episode_count == 64
    assert bundle.diagnostics.episode_count == 64
    assert bundle.diagnostics.summary.ante_8_clears == 0
    assert bundle.diagnostics.source_schema_version == bundle.source.schema_version
