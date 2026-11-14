import json
import shutil
from types import SimpleNamespace

import pytest

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.episode_backend import PPOHeadlessBackend
from games.balatro.env.ppo_campaign import CompletedPPOCampaign
from games.balatro.env.ppo_candidate_evaluation import PPOCandidateIdentity
from games.balatro.env.ppo_contract import (
    PPO_POLICY_OUTPUT_SCHEMA,
    PPO_TRAINING_CONTRACT,
    PPOPolicyOutput,
    PPOTrainingRun,
)
from games.balatro.env.ppo_promotion_evaluation import (
    BaselineEpisodeEvidence,
    PPOPromotionEvaluationError,
    execute_and_publish_ppo_promotion,
    execute_baseline_episode,
)
from games.balatro.env.random_baseline import RANDOM_LEGAL_BASELINE_VERSION
from games.balatro.env.state import RunStatus
from games.balatro.env.symbolic_baseline import SYMBOLIC_HEADLESS_BASELINE_VERSION


class _OneCardTacticalPolicy:
    def decide(self, state):
        return SimpleNamespace(action=BalatroAction(PLAY_CARDS, cards=[state.hand[0]]))


class _SelectBlindModel:
    parameter_sha256 = "5" * 64

    def infer(self, observation, action_mask):
        probabilities = [0.0] * PPO_TRAINING_CONTRACT.action_size
        probabilities[next(index for index, allowed in enumerate(action_mask.values) if allowed)] = 1.0
        return PPOPolicyOutput(
            schema_version=PPO_POLICY_OUTPUT_SCHEMA,
            observation_version=PPO_TRAINING_CONTRACT.observation_version,
            action_version=PPO_TRAINING_CONTRACT.action_version,
            probabilities=tuple(probabilities),
            value_estimate=0.0,
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


class _UniqueEntropy:
    def __init__(self):
        self.calls = 0

    def __call__(self, size):
        self.calls += 1
        return bytes([self.calls]) * size


@pytest.fixture(scope="module")
def published_evaluation(tmp_path_factory):
    destination = tmp_path_factory.mktemp("atomic-promotion") / "promotion"
    entropy = _UniqueEntropy()
    progress = []
    published = execute_and_publish_ppo_promotion(
        _campaign(),
        destination,
        entropy_source=entropy,
        environment_factory=_environment,
        symbolic_decider=_symbolic_first,
        progress_callback=lambda stage, completed, total: progress.append(
            (stage, completed, total)
        ),
    )
    return published, destination, entropy, progress


def test_env_ppo_baseline_executor_returns_exact_terminal_trace():
    evidence = execute_baseline_episode(
        RANDOM_LEGAL_BASELINE_VERSION,
        game_seed="EVAL0001",
        policy_seed="POLICY0001",
        environment_factory=_environment,
    )

    assert isinstance(evidence, BaselineEpisodeEvidence)
    assert evidence.status is RunStatus.LOSS
    assert evidence.action_count == 1
    assert len(evidence.frames) == 2
    assert evidence.frames[0].state.phase == "BLIND_SELECT"
    assert evidence.frames[-1].state.phase == "GAME_OVER"

    symbolic = execute_baseline_episode(
        SYMBOLIC_HEADLESS_BASELINE_VERSION,
        game_seed="EVAL0002",
        policy_seed=None,
        environment_factory=_environment,
    )
    assert symbolic.status is RunStatus.LOSS
    assert symbolic.action_count == 1


def test_env_ppo_atomic_promotion_publishes_complete_run_and_resumes(
    published_evaluation,
):
    first, destination, entropy, progress = published_evaluation

    assert first.directory == destination.resolve()
    assert first.candidate_sha256 == PPOCandidateIdentity.from_completed_campaign(_campaign()).sha256
    assert first.promoted is False
    assert len(first.artifact_sha256s) == 27
    assert (destination / "final.json").is_file()
    assert len(tuple(destination.iterdir())) == 28
    assert entropy.calls == 4
    fixed_source = json.loads((destination / "fixed-baselines.json").read_text())
    fixed_diagnostics = json.loads(
        (destination / "fixed-baseline-diagnostics.json").read_text()
    )
    assert len(fixed_source["episodes"]) == 128
    assert len(fixed_diagnostics["episodes"]) == 128
    assert tuple(item["ante_8_clears"] for item in fixed_diagnostics["baselines"]) == (0, 0)
    assert progress[0] == ("creating_manifests", 0, 10)
    assert progress[-1] == ("complete", 10, 10)
    assert [item[1] for item in progress] == sorted(item[1] for item in progress)

    resumed = execute_and_publish_ppo_promotion(
        _campaign(),
        destination,
        entropy_source=lambda size: (_ for _ in ()).throw(AssertionError("must not sample")),
        environment_factory=lambda stream: (_ for _ in ()).throw(AssertionError("must not run")),
        symbolic_decider=_symbolic_first,
    )
    assert resumed == first


def test_env_ppo_atomic_promotion_rejects_tampered_resume(
    tmp_path, published_evaluation
):
    published, source, _, _ = published_evaluation
    destination = tmp_path / "promotion"
    shutil.copytree(source, destination)
    artifact = destination / published.artifact_sha256s[0][0]
    artifact.write_bytes(artifact.read_bytes() + b"\n")

    with pytest.raises(PPOPromotionEvaluationError, match="digest mismatch"):
        execute_and_publish_ppo_promotion(_campaign(), destination)


def test_env_ppo_atomic_promotion_failure_publishes_nothing(tmp_path):
    destination = tmp_path / "promotion"

    def fail_environment(stream):
        raise RuntimeError("exact backend failed")

    with pytest.raises(RuntimeError, match="exact backend failed"):
        execute_and_publish_ppo_promotion(
            _campaign(),
            destination,
            entropy_source=_UniqueEntropy(),
            environment_factory=fail_environment,
            symbolic_decider=_symbolic_first,
        )

    assert not destination.exists()
    assert not tuple(tmp_path.glob(".promotion.*.tmp"))


def test_env_ppo_baseline_executor_rejects_unsupported_and_bad_seed_contracts():
    with pytest.raises(PPOPromotionEvaluationError, match="unsupported"):
        execute_baseline_episode(
            "UNKNOWN",
            game_seed="EVAL",
            policy_seed=None,
            environment_factory=_environment,
        )
    with pytest.raises(TypeError, match="baseline seed"):
        execute_baseline_episode(
            RANDOM_LEGAL_BASELINE_VERSION,
            game_seed="EVAL",
            policy_seed=None,
            environment_factory=_environment,
        )
    with pytest.raises(PPOPromotionEvaluationError, match="policy seed"):
        BaselineEpisodeEvidence(
            SYMBOLIC_HEADLESS_BASELINE_VERSION,
            "EVAL",
            "DRIFT",
            RunStatus.LOSS,
            1,
            (),
        )
