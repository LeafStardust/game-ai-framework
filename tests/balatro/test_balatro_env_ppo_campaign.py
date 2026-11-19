import json
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from games.balatro.env.environment import BalatroHeadlessEnvironment
from games.balatro.env.ppo_campaign import (
    CHECKPOINT_NAME,
    CompletedPPOCampaign,
    FINAL_NAME,
    PPO_CAMPAIGN_FINAL_VERSION,
    PPO_CAMPAIGN_VERSION,
    PPO_PROGRESS_STUDY_BATCH_LIMIT,
    PPO_PARALLEL_COLLECTION_VERSION,
    PPO_TACTICAL_FACTORY_VERSION,
    PROGRESS_NAME,
    _atomic_write,
    _canonical_bytes,
    _checkpoint_payload,
    _is_exact_immediately_stale_progress,
    _reconcile_progress_artifact,
    _restore_session,
    _state_manifest,
    make_ppo_progress_training_environment,
    make_ppo_training_environment,
    load_completed_ppo_campaign,
    run_ppo_campaign,
)
from games.balatro.env.ppo_contract import (
    PPO_PROGRESS_TRAINING_CONTRACT,
    PPOContractError,
    PPOTrainingRun,
)
from games.balatro.live.hand_action_policy import (
    SEARCH_SCHEDULE_SELECTIVE,
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

    def advance_parallel(
        self,
        *,
        maximum_episodes,
        maximum_batches,
        wave_collector,
        on_episode_committed,
    ):
        assert callable(wave_collector)
        batches_before = self.learner.completed_batch_count
        for _ in range(maximum_episodes):
            if (
                self.complete
                or self.learner.completed_batch_count - batches_before
                >= maximum_batches
            ):
                break
            self.advance(maximum_episodes=1)
            on_episode_committed(self, object())

    def serialize(self):
        return {"fake_episode_count": self.episode_count}


def _fake_opener(opened):
    def open_session(run, payload, environment_factory):
        opened.append(payload)
        if payload is None:
            return _FakeSession(run)
        assert payload["version"] == PPO_CAMPAIGN_VERSION
        assert payload["tactical_factory_version"] == PPO_TACTICAL_FACTORY_VERSION
        assert payload["parallel_collection_version"] == PPO_PARALLEL_COLLECTION_VERSION
        assert payload["training_run"] == run.as_dict()
        return _FakeSession(run, payload["session"]["fake_episode_count"])

    return open_session


def _write_completed_campaign(directory, run, session):
    checkpoint_bytes = _canonical_bytes(_checkpoint_payload(run, session))
    (directory / CHECKPOINT_NAME).write_bytes(checkpoint_bytes)
    progress = _state_manifest(run, session, sha256(checkpoint_bytes).hexdigest())
    progress_bytes = _canonical_bytes(progress)
    (directory / PROGRESS_NAME).write_bytes(progress_bytes)
    final = {
        **progress,
        "version": PPO_CAMPAIGN_FINAL_VERSION,
        "parameter_sha256": session.learner.model.parameter_sha256,
    }
    final_bytes = _canonical_bytes(final)
    (directory / FINAL_NAME).write_bytes(final_bytes)
    return checkpoint_bytes, progress_bytes, final_bytes


def test_env_ppo_completed_campaign_loader_restores_exact_linked_owner(
    tmp_path, monkeypatch
):
    run = PPOTrainingRun.from_seed("COMPLETED")
    session = _FakeSession(run, episode_count=3)
    checkpoint_bytes, progress_bytes, final_bytes = _write_completed_campaign(
        tmp_path, run, session
    )
    restored = []

    def restore(actual_run, payload, environment_factory):
        restored.append((actual_run, payload, environment_factory))
        return session

    monkeypatch.setattr("games.balatro.env.ppo_campaign._restore_session", restore)
    environment_factory = object()
    result = load_completed_ppo_campaign(
        tmp_path, environment_factory=environment_factory
    )

    assert isinstance(result, CompletedPPOCampaign)
    assert result.training_run == run
    assert result.session is session
    assert result.checkpoint_sha256 == sha256(checkpoint_bytes).hexdigest()
    assert result.progress_sha256 == sha256(progress_bytes).hexdigest()
    assert result.final_sha256 == sha256(final_bytes).hexdigest()
    assert result.policy_parameter_sha256 == "f" * 64
    assert restored == [(run, json.loads(checkpoint_bytes), environment_factory)]


@pytest.mark.parametrize("missing", (CHECKPOINT_NAME, PROGRESS_NAME, FINAL_NAME))
def test_env_ppo_completed_campaign_loader_requires_all_artifacts(
    tmp_path, monkeypatch, missing
):
    run = PPOTrainingRun.from_seed("MISSING")
    session = _FakeSession(run, episode_count=3)
    _write_completed_campaign(tmp_path, run, session)
    (tmp_path / missing).unlink()

    with pytest.raises(PPOContractError, match="requires checkpoint, progress, and final"):
        load_completed_ppo_campaign(tmp_path)


def test_env_ppo_completed_campaign_loader_rejects_drift_and_noncanonical_json(
    tmp_path, monkeypatch
):
    run = PPOTrainingRun.from_seed("DRIFT")
    session = _FakeSession(run, episode_count=3)
    _write_completed_campaign(tmp_path, run, session)
    monkeypatch.setattr(
        "games.balatro.env.ppo_campaign._restore_session",
        lambda actual_run, payload, environment_factory: session,
    )

    progress_path = tmp_path / PROGRESS_NAME
    progress = json.loads(progress_path.read_text(encoding="utf-8"))
    progress["checkpoint_sha256"] = "0" * 64
    progress_path.write_bytes(_canonical_bytes(progress))
    with pytest.raises(PPOContractError, match="progress does not match checkpoint"):
        load_completed_ppo_campaign(tmp_path)

    _write_completed_campaign(tmp_path, run, session)
    final_path = tmp_path / FINAL_NAME
    final_path.write_text(
        json.dumps(json.loads(final_path.read_text(encoding="utf-8")), indent=2),
        encoding="utf-8",
    )
    with pytest.raises(PPOContractError, match="final artifact is not canonical JSON"):
        load_completed_ppo_campaign(tmp_path)


def test_env_ppo_completed_campaign_loader_rejects_incomplete_checkpoint(
    tmp_path, monkeypatch
):
    run = PPOTrainingRun.from_seed("INCOMPLETE")
    complete = _FakeSession(run, episode_count=3)
    _write_completed_campaign(tmp_path, run, complete)
    incomplete = _FakeSession(run, episode_count=2)
    monkeypatch.setattr(
        "games.balatro.env.ppo_campaign._restore_session",
        lambda actual_run, payload, environment_factory: incomplete,
    )

    with pytest.raises(PPOContractError, match="not at the frozen schedule end"):
        load_completed_ppo_campaign(tmp_path)


def test_env_ppo_campaign_starts_resumes_and_emits_final_manifest(tmp_path):
    opened = []
    first = run_ppo_campaign(
        "CAMPAIGN",
        tmp_path,
        maximum_episodes=2,
        maximum_batches=2,
        maximum_workers=2,
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
        maximum_batches=1,
        maximum_workers=2,
        session_opener=_fake_opener(opened),
    )

    assert opened[1]["session"] == {"fake_episode_count": 2}
    assert second["version"] == PPO_CAMPAIGN_FINAL_VERSION
    assert second["complete"] is True
    assert second["completed_batch_count"] == 3
    assert second["parameter_sha256"] == "f" * 64
    assert json.loads((tmp_path / FINAL_NAME).read_text(encoding="utf-8")) == second


def test_env_ppo_campaign_selects_isolated_progress_contract_environment_and_observer(
    tmp_path,
):
    opened = []
    observed = []

    def opener(run, payload, environment_factory):
        opened.append((run, payload, environment_factory))
        return _FakeSession(run)

    progress = run_ppo_campaign(
        "PROGRESS-PILOT",
        tmp_path,
        maximum_episodes=1,
        maximum_batches=1,
        maximum_workers=1,
        session_opener=opener,
        episode_wave_collector=lambda *args: (),
        training_contract=PPO_PROGRESS_TRAINING_CONTRACT,
        episode_commit_observer=lambda session, episode: observed.append(
            (session, episode)
        ),
    )

    run, payload, environment_factory = opened[0]
    assert payload is None
    assert run.contract_sha256 == PPO_PROGRESS_TRAINING_CONTRACT.sha256
    assert environment_factory is make_ppo_progress_training_environment
    assert len(observed) == 1
    assert progress["training_run_sha256"] == run.sha256


def test_env_ppo_campaign_rejects_progress_multi_batch_and_resume(tmp_path):
    with pytest.raises(PPOContractError, match="one fresh pilot batch"):
        run_ppo_campaign(
            "PROGRESS-BOUND",
            tmp_path,
            maximum_episodes=1,
            maximum_batches=2,
            maximum_workers=1,
            session_opener=_fake_opener([]),
            episode_wave_collector=lambda *args: (),
            training_contract=PPO_PROGRESS_TRAINING_CONTRACT,
        )


def test_env_ppo_campaign_allows_only_exact_capped_progress_study_resume(tmp_path):
    opened = []
    first = run_ppo_campaign(
        "PROGRESS-STUDY",
        tmp_path,
        maximum_episodes=1,
        maximum_batches=1,
        maximum_workers=1,
        session_opener=_fake_opener(opened),
        episode_wave_collector=lambda *args: (),
        training_contract=PPO_PROGRESS_TRAINING_CONTRACT,
        progress_study_batch_limit=PPO_PROGRESS_STUDY_BATCH_LIMIT,
    )
    second = run_ppo_campaign(
        "PROGRESS-STUDY",
        tmp_path,
        maximum_episodes=1,
        maximum_batches=1,
        maximum_workers=1,
        session_opener=_fake_opener(opened),
        episode_wave_collector=lambda *args: (),
        training_contract=PPO_PROGRESS_TRAINING_CONTRACT,
        progress_study_batch_limit=PPO_PROGRESS_STUDY_BATCH_LIMIT,
    )

    assert first["completed_batch_count"] == 1
    assert second["completed_batch_count"] == 2
    assert opened[1]["session"] == {"fake_episode_count": 1}

    with pytest.raises(PPOContractError, match="must be exactly 8"):
        run_ppo_campaign(
            "OTHER-STUDY",
            tmp_path / "other",
            maximum_episodes=1,
            maximum_batches=1,
            maximum_workers=1,
            session_opener=_fake_opener([]),
            episode_wave_collector=lambda *args: (),
            training_contract=PPO_PROGRESS_TRAINING_CONTRACT,
            progress_study_batch_limit=4,
        )

    with pytest.raises(PPOContractError, match="exceeds its 8-batch cap"):
        run_ppo_campaign(
            "CAPPED-STUDY",
            tmp_path / "capped",
            maximum_episodes=2,
            maximum_batches=2,
            maximum_workers=1,
            session_opener=lambda run, payload, environment_factory: _FakeSession(
                run, 7
            ),
            episode_wave_collector=lambda *args: (),
            training_contract=PPO_PROGRESS_TRAINING_CONTRACT,
            progress_study_batch_limit=PPO_PROGRESS_STUDY_BATCH_LIMIT,
        )

    with pytest.raises(PPOContractError, match="sparse PPO campaign"):
        run_ppo_campaign(
            "SPARSE-STUDY",
            tmp_path / "sparse",
            maximum_episodes=1,
            maximum_batches=1,
            maximum_workers=1,
            session_opener=_fake_opener([]),
            episode_wave_collector=lambda *args: (),
            progress_study_batch_limit=PPO_PROGRESS_STUDY_BATCH_LIMIT,
        )

    (tmp_path / CHECKPOINT_NAME).write_text("{}", encoding="utf-8")
    with pytest.raises(PPOContractError, match="one fresh pilot batch"):
        run_ppo_campaign(
            "PROGRESS-BOUND",
            tmp_path,
            maximum_episodes=1,
            maximum_batches=1,
            maximum_workers=1,
            session_opener=_fake_opener([]),
            episode_wave_collector=lambda *args: (),
            training_contract=PPO_PROGRESS_TRAINING_CONTRACT,
        )


def test_env_ppo_campaign_observer_failure_precedes_checkpoint_publication(tmp_path):
    def reject_observation(session, episode):
        raise PPOContractError("journal publication failed")

    with pytest.raises(PPOContractError, match="journal publication failed"):
        run_ppo_campaign(
            "OBSERVER-ORDER",
            tmp_path,
            maximum_episodes=1,
            maximum_batches=1,
            maximum_workers=1,
            session_opener=_fake_opener([]),
            episode_wave_collector=lambda *args: (),
            episode_commit_observer=reject_observation,
        )

    assert not (tmp_path / CHECKPOINT_NAME).exists()
    assert not (tmp_path / PROGRESS_NAME).exists()


def test_env_ppo_campaign_rebuilds_progress_from_checkpoint_on_resume(tmp_path):
    run_ppo_campaign(
        "REBUILD",
        tmp_path,
        maximum_episodes=1,
        maximum_batches=1,
        maximum_workers=2,
        session_opener=_fake_opener([]),
    )
    (tmp_path / PROGRESS_NAME).unlink()

    progress = run_ppo_campaign(
        "REBUILD",
        tmp_path,
        maximum_episodes=1,
        maximum_batches=1,
        maximum_workers=2,
        session_opener=_fake_opener([]),
    )

    assert progress["completed_batch_count"] == 2
    assert (tmp_path / PROGRESS_NAME).exists()


def test_env_ppo_campaign_repairs_exact_one_episode_interrupted_progress(tmp_path):
    run = PPOTrainingRun.from_seed("INTERRUPTED")
    checkpoint_bytes = b'{}'
    session = SimpleNamespace(
        learner=SimpleNamespace(
            completed_batch_count=1,
            total_consumed_environment_transitions=2048,
            assembler=SimpleNamespace(
                next_episode_indices=(8, 1, 2, 3, 4, 5, 6, 7)
            ),
        ),
        optimizer_consumed_transitions=2048,
        complete=False,
    )
    expected = _state_manifest(
        run,
        session,
        sha256(checkpoint_bytes).hexdigest(),
    )
    previous = dict(expected)
    previous["checkpoint_sha256"] = "a" * 64
    previous["completed_batch_count"] = 0
    previous["optimizer_consumed_transitions"] = 0
    previous["collected_environment_transitions"] = 0
    previous["next_episode_indices"] = list(range(8))
    previous["complete"] = False
    progress_path = tmp_path / PROGRESS_NAME
    progress_path.write_text(
        json.dumps(previous, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )

    assert _is_exact_immediately_stale_progress(previous, expected)
    repaired = _reconcile_progress_artifact(
        run,
        session,
        checkpoint_bytes,
        progress_path,
    )

    assert repaired == expected
    assert repaired == json.loads(progress_path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "mutate",
    (
        lambda value: value.update(training_run_sha256="c" * 64),
        lambda value: value.update(collected_environment_transitions=4097),
        lambda value: value.update(next_episode_indices=[8, 1, 2, 3, 4, 5, 6, 7]),
        lambda value: value.update(completed_batch_count=2),
        lambda value: value.update(complete=True),
    ),
)
def test_env_ppo_campaign_rejects_nonexact_progress_mismatch(tmp_path, mutate):
    run = PPOTrainingRun.from_seed("MISMATCH")
    checkpoint_bytes = b'{}'
    session = SimpleNamespace(
        learner=SimpleNamespace(
            completed_batch_count=1,
            total_consumed_environment_transitions=2048,
            assembler=SimpleNamespace(
                next_episode_indices=(8, 1, 2, 3, 4, 5, 6, 7)
            ),
        ),
        optimizer_consumed_transitions=2048,
        complete=False,
    )
    expected = _state_manifest(
        run,
        session,
        sha256(checkpoint_bytes).hexdigest(),
    )
    previous = dict(expected)
    previous["checkpoint_sha256"] = "a" * 64
    previous["completed_batch_count"] = 0
    previous["optimizer_consumed_transitions"] = 0
    previous["collected_environment_transitions"] = 0
    previous["next_episode_indices"] = list(range(8))
    previous["complete"] = False
    mutate(previous)
    progress_path = tmp_path / PROGRESS_NAME
    original = json.dumps(previous, sort_keys=True, separators=(",", ":"))
    progress_path.write_text(original, encoding="utf-8")

    with pytest.raises(PPOContractError, match="does not match checkpoint"):
        _reconcile_progress_artifact(
            run,
            session,
            checkpoint_bytes,
            progress_path,
        )

    assert progress_path.read_text(encoding="utf-8") == original


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


def test_env_ppo_campaign_atomic_write_retries_transient_access_denial(
    tmp_path, monkeypatch
):
    destination = tmp_path / "artifact.json"
    destination.write_bytes(b"old")
    real_replace = __import__("os").replace
    attempts = []
    delays = []

    def transiently_denied(source, target):
        attempts.append((Path(source), Path(target)))
        if len(attempts) < 3:
            raise PermissionError(13, "access denied", target)
        real_replace(source, target)

    monkeypatch.setattr(
        "games.balatro.env.ppo_campaign.os.replace", transiently_denied
    )
    monkeypatch.setattr("games.balatro.env.ppo_campaign.sleep", delays.append)

    _atomic_write(destination, b"new")

    assert destination.read_bytes() == b"new"
    assert len(attempts) == 3
    assert delays == [0.025, 0.05]
    assert not (tmp_path / ".artifact.json.tmp").exists()


def test_env_ppo_campaign_atomic_write_fails_closed_after_access_denial_limit(
    tmp_path, monkeypatch
):
    destination = tmp_path / "artifact.json"
    destination.write_bytes(b"old")
    attempts = []
    delays = []

    def persistently_denied(source, target):
        attempts.append((Path(source), Path(target)))
        raise PermissionError(13, "access denied", target)

    monkeypatch.setattr(
        "games.balatro.env.ppo_campaign.os.replace", persistently_denied
    )
    monkeypatch.setattr("games.balatro.env.ppo_campaign.sleep", delays.append)

    with pytest.raises(PermissionError, match="access denied"):
        _atomic_write(destination, b"new")

    assert destination.read_bytes() == b"old"
    assert len(attempts) == 20
    assert len(delays) == 19
    assert delays[:4] == [0.025, 0.05, 0.1, 0.2]
    assert delays[4:] == [0.25] * 15
    assert not (tmp_path / ".artifact.json.tmp").exists()


def test_env_ppo_campaign_rejects_stale_and_cross_run_artifacts(tmp_path):
    (tmp_path / PROGRESS_NAME).write_text("{}", encoding="utf-8")
    with pytest.raises(PPOContractError, match="without a checkpoint"):
        run_ppo_campaign(
            "STALE",
            tmp_path,
            maximum_episodes=1,
            maximum_batches=1,
            maximum_workers=2,
            session_opener=_fake_opener([]),
        )

    run = PPOTrainingRun.from_seed("OWNER")
    payload = {
        "version": PPO_CAMPAIGN_VERSION,
        "tactical_factory_version": PPO_TACTICAL_FACTORY_VERSION,
        "parallel_collection_version": PPO_PARALLEL_COLLECTION_VERSION,
        "training_run": run.as_dict(),
        "session": {},
    }
    with pytest.raises(PPOContractError, match="training-run provenance"):
        _restore_session(PPOTrainingRun.from_seed("OTHER"), payload, object())

    payload["tactical_factory_version"] = "old"
    with pytest.raises(PPOContractError, match="tactical factory version"):
        _restore_session(run, payload, object())

    payload["tactical_factory_version"] = PPO_TACTICAL_FACTORY_VERSION
    payload["parallel_collection_version"] = "old"
    with pytest.raises(PPOContractError, match="parallel collection version"):
        _restore_session(run, payload, object())

    payload["parallel_collection_version"] = PPO_PARALLEL_COLLECTION_VERSION
    payload["version"] = "balatro-red-white-ppo-campaign-v2"
    with pytest.raises(PPOContractError, match="campaign version"):
        _restore_session(run, payload, object())


def test_env_ppo_campaign_rejects_pre_selective_tactical_factory_checkpoint():
    run = PPOTrainingRun.from_seed("PRE-SELECTIVE")
    payload = {
        "version": PPO_CAMPAIGN_VERSION,
        "tactical_factory_version": "balatro-red-white-ppo-tactical-factory-v1",
        "parallel_collection_version": PPO_PARALLEL_COLLECTION_VERSION,
        "training_run": run.as_dict(),
        "session": {},
    }

    with pytest.raises(PPOContractError, match="tactical factory version"):
        _restore_session(run, payload, object())


def test_env_ppo_campaign_rejects_final_artifact_for_incomplete_checkpoint(tmp_path):
    run_ppo_campaign(
        "INCOMPLETE",
        tmp_path,
        maximum_episodes=1,
        maximum_batches=1,
        maximum_workers=2,
        session_opener=_fake_opener([]),
    )
    (tmp_path / FINAL_NAME).write_text("{}", encoding="utf-8")

    with pytest.raises(PPOContractError, match="contradicts an incomplete"):
        run_ppo_campaign(
            "INCOMPLETE",
            tmp_path,
            maximum_episodes=1,
            maximum_batches=1,
            maximum_workers=2,
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
    assert engine.search_schedule_mode == SEARCH_SCHEDULE_SELECTIVE
    assert engine.max_search_seconds is None
    assert PPO_CAMPAIGN_VERSION == "balatro-red-white-ppo-campaign-v13"
    assert PPO_PARALLEL_COLLECTION_VERSION == (
        "balatro-red-white-ppo-parallel-collection-v11"
    )
    with pytest.raises(PPOContractError, match="stream index"):
        make_ppo_training_environment(8)


@pytest.mark.parametrize("maximum_workers", (0, 9, True))
def test_env_ppo_campaign_rejects_invalid_worker_bounds(tmp_path, maximum_workers):
    with pytest.raises(PPOContractError, match="maximum workers"):
        run_ppo_campaign(
            "WORKER-BOUND",
            tmp_path,
            maximum_episodes=1,
            maximum_batches=1,
            maximum_workers=maximum_workers,
            session_opener=_fake_opener([]),
        )


@pytest.mark.parametrize("maximum_batches", (0, 1025, True))
def test_env_ppo_campaign_rejects_invalid_batch_bounds(tmp_path, maximum_batches):
    with pytest.raises(PPOContractError, match="maximum batches"):
        run_ppo_campaign(
            "BATCH-BOUND",
            tmp_path,
            maximum_episodes=1,
            maximum_batches=maximum_batches,
            maximum_workers=1,
            session_opener=_fake_opener([]),
        )
