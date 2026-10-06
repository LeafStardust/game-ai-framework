import json
from hashlib import sha256
from pathlib import Path

import pytest

import games.balatro.env.ppo_checkpoint_search_subowners as checkpoint_search
from games.balatro.env.ppo_campaign import (
    _canonical_bytes,
    _checkpoint_payload,
    make_ppo_training_environment,
)
from games.balatro.env.ppo_checkpoint_search_subowners import (
    EXPECTED_PREFIX,
    PPO_CHECKPOINT_SEARCH_SUBOWNER_SCHEMA,
    trace_checkpoint_search_subowners,
    write_checkpoint_search_subowner_report,
)
from games.balatro.env.ppo_contract import PPOContractError, PPOTrainingRun
from games.balatro.env.ppo_tactical_performance import (
    PPO_TACTICAL_CANDIDATE_SUBOWNER_SCHEMA,
    PPOTacticalCandidateHelperCost,
    PPOTacticalCandidateSubownerReport,
    _PPOTacticalScopedSubownerTrace,
)
from games.balatro.env.ppo_training_session import PPOTrainingSession
from tests.balatro.test_balatro_env_ppo_batch import _episode


def _checkpoint(tmp_path, seed="CHECKPOINT-SEARCH"):
    run = PPOTrainingRun.from_seed(seed)
    session = PPOTrainingSession(run, make_ppo_training_environment)
    session.learner.assembler._next_episode_indices = list(range(632, 640))
    path = tmp_path / "checkpoint.json"
    content = _canonical_bytes(_checkpoint_payload(run, session))
    path.write_bytes(content)
    return run, path, content


def _target_report(root_seed="CHECKPOINT-SEARCH"):
    digest, action, indices, attempts = EXPECTED_PREFIX[-1]
    return PPOTacticalCandidateSubownerReport(
        schema=PPO_TACTICAL_CANDIDATE_SUBOWNER_SCHEMA,
        root_seed=root_seed,
        episode_index=637,
        stream_index=5,
        game_seed=PPOTrainingRun.from_seed(root_seed).game_seed(637),
        verified_prefix_decisions=12,
        target_decision_index=11,
        public_input_sha256=digest,
        action=action,
        selected_hand_indices=indices,
        search_attempts=attempts,
        evaluation_cache_hits=2,
        evaluation_cache_misses=3,
        generated_consumable_transition_calls=0,
        generated_consumable_inert_calls=0,
        generated_consumable_eight_ball_capable_calls=0,
        generated_consumable_main_generator_capable_calls=0,
        generated_consumable_sixth_sense_capable_calls=0,
        hook_forced_branch_sets=0,
        hook_forced_branches=0,
        hook_discard_projection_calls=0,
        hook_outcome_aggregation_calls=0,
        hook_aggregated_outcomes=0,
        discard_active_joker_selection_calls=0,
        discard_active_jokers_selected=0,
        discard_joker_application_calls=0,
        discard_jokers_applied=0,
        total_elapsed_seconds=8.0,
        candidate_generation_elapsed_seconds=3.0,
        helper_costs=(PPOTacticalCandidateHelperCost("_evaluator_evaluate", 5, 2.5),),
        reconstruct_type_sample_limit=100_000,
        reconstruct_type_sampled_calls=0,
        reconstruct_type_samples=(),
        state_card_sample_limit=100_000,
        state_card_validation_sampled_calls=0,
        state_card_validation_elapsed_seconds=0.0,
        state_card_shallow_copy_sampled_calls=0,
        state_card_shallow_copy_elapsed_seconds=0.0,
        residual_candidate_elapsed_seconds=0.0,
    )


def _scoped(root_seed="CHECKPOINT-SEARCH"):
    return _PPOTacticalScopedSubownerTrace(
        report=_target_report(root_seed),
        search_evaluation_elapsed_seconds=4.0,
        policy_arbitration_elapsed_seconds=0.75,
        other_elapsed_seconds=0.25,
        residual_search_evaluation_elapsed_seconds=1.5,
    )


def test_checkpoint_search_prefix_is_pinned_to_committed_tactical_report():
    payload = json.loads(
        Path(
            "docs/balatro/BALATRO_PPO_BATCH2_EPISODE_637_TACTICAL.json"
        ).read_text(encoding="utf-8")
    )
    prefix = tuple(
        (
            decision["public_input_sha256"],
            decision["action"],
            tuple(decision["selected_hand_indices"]),
            tuple(tuple(attempt) for attempt in decision["search_attempts"]),
        )
        for decision in payload["decisions"][:12]
    )

    assert payload["episode_index"] == 637
    assert payload["stream_index"] == 5
    assert EXPECTED_PREFIX == prefix


def test_checkpoint_search_subowners_are_exact_read_only_and_provenanced(tmp_path):
    run, path, checkpoint_bytes = _checkpoint(tmp_path)
    observed = {}

    def trace(**kwargs):
        observed.update(kwargs)
        return _scoped()

    report = trace_checkpoint_search_subowners(
        "CHECKPOINT-SEARCH",
        path,
        subowner_tracer=trace,
        episode_collector=lambda *_args, **_kwargs: _episode(run, 637, length=3),
    )

    episode = _episode(run, 637, length=3)
    assert report.schema == PPO_CHECKPOINT_SEARCH_SUBOWNER_SCHEMA
    assert report.checkpoint_sha256 == sha256(checkpoint_bytes).hexdigest()
    assert report.training_run_sha256 == run.sha256
    assert report.session_sha256_before == report.session_sha256_after
    assert report.policy_parameter_sha256
    assert report.episode_sha256 == sha256(episode.to_json().encode()).hexdigest()
    assert report.environment_transitions == 3
    assert report.committed is False
    assert report.search_evaluation_elapsed_seconds == 4.0
    assert report.target == _target_report()
    assert observed["expected_prefix"] == EXPECTED_PREFIX
    assert observed["target_index"] == 11
    assert observed["helper_scope"] == "search_evaluation"
    assert callable(observed["policy"])


def test_checkpoint_search_subowners_fail_closed_on_scope_and_session_drift(
    monkeypatch, tmp_path
):
    run, path, _ = _checkpoint(tmp_path, seed="CHECKPOINT-SEARCH-DRIFT")
    with pytest.raises(PPOContractError, match="invalid scope"):
        trace_checkpoint_search_subowners(
            "CHECKPOINT-SEARCH-DRIFT",
            path,
            subowner_tracer=lambda **_kwargs: object(),
            episode_collector=lambda *_args, **_kwargs: _episode(run, 637, length=1),
        )

    original_restore = checkpoint_search._restore_session
    restored = {}

    def capture(training_run, payload, environment_factory):
        session = original_restore(training_run, payload, environment_factory)
        restored["session"] = session
        return session

    monkeypatch.setattr(checkpoint_search, "_restore_session", capture)

    def mutate(**_kwargs):
        restored["session"].learner.optimizer._rng.random()
        return _scoped("CHECKPOINT-SEARCH-DRIFT")

    with pytest.raises(PPOContractError, match="mutated campaign state"):
        trace_checkpoint_search_subowners(
            "CHECKPOINT-SEARCH-DRIFT",
            path,
            subowner_tracer=mutate,
            episode_collector=lambda *_args, **_kwargs: _episode(run, 637, length=1),
        )


def test_checkpoint_search_subowner_report_is_atomically_canonical(tmp_path):
    run, path, _ = _checkpoint(tmp_path, seed="CHECKPOINT-SEARCH-WRITE")
    report = trace_checkpoint_search_subowners(
        "CHECKPOINT-SEARCH-WRITE",
        path,
        subowner_tracer=lambda **_kwargs: _scoped("CHECKPOINT-SEARCH-WRITE"),
        episode_collector=lambda *_args, **_kwargs: _episode(run, 637, length=1),
    )
    output = tmp_path / "search.json"
    digest = write_checkpoint_search_subowner_report(output, report)

    assert output.read_bytes() == report.to_json().encode()
    assert digest == sha256(output.read_bytes()).hexdigest()
    assert json.loads(output.read_text())["target"]["target_decision_index"] == 11


def test_checkpoint_search_subowners_reject_noncanonical_checkpoint(tmp_path):
    _, path, content = _checkpoint(tmp_path, seed="CHECKPOINT-SEARCH-NONCANONICAL")
    path.write_bytes(content + b"\n")

    with pytest.raises(PPOContractError, match="not canonical"):
        trace_checkpoint_search_subowners(
            "CHECKPOINT-SEARCH-NONCANONICAL",
            path,
        )
