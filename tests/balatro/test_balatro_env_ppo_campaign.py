import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.ppo_campaign import (
    CHECKPOINT_NAME,
    FINAL_NAME,
    PPO_CAMPAIGN_FINAL_VERSION,
    PPO_CAMPAIGN_VERSION,
    PPO_TACTICAL_FACTORY_VERSION,
    PROGRESS_NAME,
    _atomic_write,
    _restore_session,
    make_ppo_training_environment,
    run_ppo_campaign,
)
from games.balatro.env.ppo_contract import PPOContractError, PPOTrainingRun
from games.balatro.live.hand_action_policy import (
    SEARCH_SCHEDULE_FULL,
    LiveHandActionDecisionEngine,
)
from games.balatro.live.strategy_hand_policy import StrategyAwareLiveHandActionPolicy


class _FakeSession:
    def __init__(self, run, episode_count=0):
        self.run = run
        self.episode_count = episode_count
        self.learner = SimpleNamespace(
            completed_batch_count=episode_count,
            total_consumed_environment_transitions=episode_count * 2048,
            assembler=SimpleNamespace(
                next_episode_indices=tuple(
                    episode_count * 8 + index for index in range(8)
                )
            ),
            model=SimpleNamespace(parameter_sha256="f" * 64),
        )

    @property
    def complete(self):
        return self.episode_count == 3

    @property
    def optimizer_consumed_transitions(self):
        return self.learner.completed_batch_count * 2048

    def advance(self, *, maximum_episodes):
        assert maximum_episodes == 1
        self.episode_count += 1
        self.learner.completed_batch_count += 1
        self.learner.total_consumed_environment_transitions += 2048
        self.learner.assembler.next_episode_indices = tuple(
            self.episode_count * 8 + index for index in range(8)
        )

    def serialize(self):
        return {"fake_episode_count": self.episode_count}


def _fake_opener(opened):
    def open_session(run, payload, environment_factory):
        opened.append(payload)
        if payload is None:
            return _FakeSession(run)
        assert payload["version"] == PPO_CAMPAIGN_VERSION
        assert payload["tactical_factory_version"] == PPO_TACTICAL_FACTORY_VERSION
        assert payload["training_run"] == run.as_dict()
        return _FakeSession(run, payload["session"]["fake_episode_count"])

    return open_session


def test_env_ppo_campaign_starts_resumes_and_emits_final_manifest(tmp_path):
    opened = []
    first = run_ppo_campaign(
        "CAMPAIGN",
        tmp_path,
        maximum_episodes=2,
        session_opener=_fake_opener(opened),
    )

    assert opened == [None]
    assert first["complete"] is False
    assert first["completed_batch_count"] == 2
    assert first["optimizer_consumed_transitions"] == 4096
    assert (tmp_path / CHECKPOINT_NAME).exists()
    assert (tmp_path / PROGRESS_NAME).exists()
    assert not (tmp_path / FINAL_NAME).exists()

    second = run_ppo_campaign(
        "CAMPAIGN",
        tmp_path,
        maximum_episodes=10,
        session_opener=_fake_opener(opened),
    )

    assert opened[1]["session"] == {"fake_episode_count": 2}
    assert second["version"] == PPO_CAMPAIGN_FINAL_VERSION
    assert second["complete"] is True
    assert second["completed_batch_count"] == 3
    assert second["parameter_sha256"] == "f" * 64
    assert json.loads((tmp_path / FINAL_NAME).read_text(encoding="utf-8")) == second


def test_env_ppo_campaign_rebuilds_progress_from_checkpoint_on_resume(tmp_path):
    run_ppo_campaign(
        "REBUILD",
        tmp_path,
        maximum_episodes=1,
        session_opener=_fake_opener([]),
    )
    (tmp_path / PROGRESS_NAME).unlink()

    progress = run_ppo_campaign(
        "REBUILD",
        tmp_path,
        maximum_episodes=1,
        session_opener=_fake_opener([]),
    )

    assert progress["completed_batch_count"] == 2
    assert (tmp_path / PROGRESS_NAME).exists()


def test_env_ppo_campaign_atomic_write_preserves_previous_artifact(
    tmp_path, monkeypatch
):
    destination = tmp_path / "artifact.json"
    destination.write_bytes(b"old")

    def interrupted(source, target):
        assert Path(target) == destination
        raise OSError("interrupted")

    monkeypatch.setattr("games.balatro.env.ppo_campaign.os.replace", interrupted)
    with pytest.raises(OSError, match="interrupted"):
        _atomic_write(destination, b"new")

    assert destination.read_bytes() == b"old"
    assert not (tmp_path / ".artifact.json.tmp").exists()


def test_env_ppo_campaign_rejects_stale_and_cross_run_artifacts(tmp_path):
    (tmp_path / PROGRESS_NAME).write_text("{}", encoding="utf-8")
    with pytest.raises(PPOContractError, match="without a checkpoint"):
        run_ppo_campaign(
            "STALE",
            tmp_path,
            maximum_episodes=1,
            session_opener=_fake_opener([]),
        )

    run = PPOTrainingRun.from_seed("OWNER")
    payload = {
        "version": PPO_CAMPAIGN_VERSION,
        "tactical_factory_version": PPO_TACTICAL_FACTORY_VERSION,
        "training_run": run.as_dict(),
        "session": {},
    }
    with pytest.raises(PPOContractError, match="training-run provenance"):
        _restore_session(PPOTrainingRun.from_seed("OTHER"), payload, object())

    payload["tactical_factory_version"] = "old"
    with pytest.raises(PPOContractError, match="tactical factory version"):
        _restore_session(run, payload, object())


def test_env_ppo_campaign_rejects_final_artifact_for_incomplete_checkpoint(tmp_path):
    run_ppo_campaign(
        "INCOMPLETE",
        tmp_path,
        maximum_episodes=1,
        session_opener=_fake_opener([]),
    )
    (tmp_path / FINAL_NAME).write_text("{}", encoding="utf-8")

    with pytest.raises(PPOContractError, match="contradicts an incomplete"):
        run_ppo_campaign(
            "INCOMPLETE",
            tmp_path,
            maximum_episodes=1,
            session_opener=_fake_opener([]),
        )


def test_env_ppo_campaign_factory_freezes_production_tactical_owner():
    environment = make_ppo_training_environment(0)
    engine = environment._backend._tactical_decision_engine

    assert isinstance(environment, BalatroHeadlessEnvironment)
    assert isinstance(engine, LiveHandActionDecisionEngine)
    assert isinstance(engine.policy, StrategyAwareLiveHandActionPolicy)
    assert engine.max_horizon == 8
    assert engine.max_search_nodes == 5000
    assert engine.exact_limit == 128
    assert engine.child_exact_limit == 8
    assert engine.search_schedule_mode == SEARCH_SCHEDULE_FULL
    assert engine.max_search_seconds is None
    with pytest.raises(PPOContractError, match="stream index"):
        make_ppo_training_environment(8)
