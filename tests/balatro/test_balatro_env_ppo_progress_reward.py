import json
from copy import deepcopy

import pytest

from games.balatro.env.episode_backend import (
    PPOHeadlessBackend,
    progress_potential,
    transition_reward,
)
from games.balatro.env.ppo_contract import (
    PPO_PROGRESS_REWARD_CONTRACT,
    PPO_PROGRESS_TRAINING_CONTRACT,
    PPO_REWARD_CONTRACT,
    PPO_TRAINING_CONTRACT,
    PPOContractError,
    PPOTrainingRun,
)
from games.balatro.env.state import EnvStateFrame, RunStatus, TurnOwner
from games.balatro.env.transition import HeadlessTransitionError
from games.balatro.state import BalatroState


class _Policy:
    def decide(self, state):
        raise AssertionError("reset/serialization test must not settle a blind")


def _frame(round_index, status=RunStatus.RUNNING):
    state = BalatroState()
    state.round = round_index
    return EnvStateFrame(
        state,
        status=status,
        owner=TurnOwner.TERMINAL if status.terminal else TurnOwner.AGENT,
    )


def test_progress_reward_is_exact_public_potential_difference():
    before = _frame(3)
    after = _frame(4)
    assert progress_potential(before) == 3 / 24
    assert transition_reward(before, after, PPO_PROGRESS_REWARD_CONTRACT) == (
        0.99 * (4 / 24) - (3 / 24)
    )
    loss = _frame(4, RunStatus.LOSS)
    assert progress_potential(loss) == 0.0
    assert transition_reward(after, loss, PPO_PROGRESS_REWARD_CONTRACT) == (
        -1.0 - (4 / 24)
    )
    assert transition_reward(before, after, PPO_REWARD_CONTRACT) == 0.0
    assert transition_reward(after, loss, PPO_REWARD_CONTRACT) == -1.0


def test_discounted_progress_rewards_telescope_to_sparse_terminal_return():
    frames = [_frame(0), _frame(1), _frame(2), _frame(2, RunStatus.LOSS)]
    progress_rewards = [
        transition_reward(before, after, PPO_PROGRESS_REWARD_CONTRACT)
        for before, after in zip(frames, frames[1:])
    ]
    sparse_rewards = [
        transition_reward(before, after, PPO_REWARD_CONTRACT)
        for before, after in zip(frames, frames[1:])
    ]
    discounted_progress = sum(
        (0.99**index) * reward
        for index, reward in enumerate(progress_rewards)
    )
    discounted_sparse = sum(
        (0.99**index) * reward
        for index, reward in enumerate(sparse_rewards)
    )
    assert discounted_progress == pytest.approx(discounted_sparse)


def test_progress_reward_fails_closed_on_malformed_round_or_contract():
    malformed = _frame(0)
    malformed.state.round = True
    with pytest.raises(HeadlessTransitionError, match="round"):
        progress_potential(malformed)
    with pytest.raises(HeadlessTransitionError, match="unsupported"):
        transition_reward(_frame(0), _frame(1), "unknown")


def test_progress_backend_tags_contract_without_changing_v1_snapshot_shape():
    sparse = PPOHeadlessBackend(_Policy())
    sparse_frame = sparse.reset("SPARSE")
    sparse_payload = sparse.serialize()
    assert sparse_frame.info["reward_contract"] == PPO_REWARD_CONTRACT
    assert set(sparse_payload) == {"schema", "tactical_actions", "run"}
    explicit_sparse = PPOHeadlessBackend(
        _Policy(), reward_contract=PPO_REWARD_CONTRACT
    )
    explicit_sparse.reset("SPARSE")
    assert json.dumps(
        explicit_sparse.serialize(), sort_keys=True, separators=(",", ":")
    ).encode("utf-8") == json.dumps(
        sparse_payload, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")

    progress = PPOHeadlessBackend(
        _Policy(), reward_contract=PPO_PROGRESS_REWARD_CONTRACT
    )
    progress_frame = progress.reset("PROGRESS")
    progress_payload = progress.serialize()
    assert progress_frame.info["reward_contract"] == PPO_PROGRESS_REWARD_CONTRACT
    assert progress_payload["reward_contract"] == PPO_PROGRESS_REWARD_CONTRACT

    restored = PPOHeadlessBackend(
        _Policy(), reward_contract=PPO_PROGRESS_REWARD_CONTRACT
    )
    restored.restore(deepcopy(progress_payload))
    assert restored.serialize() == progress_payload
    with pytest.raises(HeadlessTransitionError, match="fields"):
        sparse.restore(progress_payload)


def test_progress_backend_rejects_unknown_reward_contract():
    with pytest.raises(ValueError, match="unsupported"):
        PPOHeadlessBackend(_Policy(), reward_contract="unknown")


def test_progress_training_run_is_distinct_without_changing_default_v1_bytes():
    default_run = PPOTrainingRun.from_seed("CONTRACT-BYTES")
    explicit_v1_run = PPOTrainingRun.from_seed(
        "CONTRACT-BYTES", contract=PPO_TRAINING_CONTRACT
    )
    progress_run = PPOTrainingRun.from_seed(
        "CONTRACT-BYTES", contract=PPO_PROGRESS_TRAINING_CONTRACT
    )

    assert default_run.to_json().encode("utf-8") == explicit_v1_run.to_json().encode(
        "utf-8"
    )
    assert progress_run.contract_sha256 == PPO_PROGRESS_TRAINING_CONTRACT.sha256
    assert progress_run.contract_sha256 != default_run.contract_sha256
    assert progress_run.game_seed(0) == default_run.game_seed(0)


def test_unregistered_training_contract_fails_closed():
    with pytest.raises(PPOContractError, match="digest mismatch"):
        PPOTrainingRun.from_seed("UNREGISTERED", contract=object())
