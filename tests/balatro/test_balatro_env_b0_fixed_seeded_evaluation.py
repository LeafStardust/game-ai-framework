import json
from dataclasses import replace

import pytest

from games.balatro.env.action_encoding import PUBLIC_ACTION_VERSION
from games.balatro.env.observation_encoding import PUBLIC_OBSERVATION_VERSION
from games.balatro.env.random_baseline import RANDOM_LEGAL_BASELINE_VERSION
from games.balatro.env.seeded_evaluation import (
    EVALUATED_BASELINE_VERSIONS,
    EVALUATION_DECK,
    EVALUATION_MODE,
    EVALUATION_STAKE,
    FIXED_SEEDED_CORPUS_VERSION,
    FIXED_SEEDED_CORPUS_SHA256,
    FIXED_SEEDED_EPISODE_COUNT,
    FIXED_SEEDED_EPISODES,
    FIXED_SEEDED_EVALUATION_SCHEMA,
    FixedSeededEpisodeResult,
    FixedSeededEvaluationError,
    FixedSeededEvaluationReport,
    run_fixed_seeded_evaluation,
)
from games.balatro.env.state import RunStatus
from games.balatro.env.symbolic_baseline import SYMBOLIC_HEADLESS_BASELINE_VERSION


def _result(baseline_version, spec, policy_seed, *, status=RunStatus.LOSS):
    return FixedSeededEpisodeResult.completed(
        baseline_version=baseline_version,
        episode_index=spec.episode_index,
        game_seed=spec.game_seed,
        policy_seed=policy_seed,
        status=status,
        action_count=spec.episode_index + 1,
    )


def _complete_report():
    return run_fixed_seeded_evaluation(_result)


def test_env_b0_fixed_seed_corpus_is_versioned_unique_and_pinned():
    assert len(FIXED_SEEDED_EPISODES) == FIXED_SEEDED_EPISODE_COUNT == 64
    assert len({spec.game_seed for spec in FIXED_SEEDED_EPISODES}) == 64
    assert len({spec.random_policy_seed for spec in FIXED_SEEDED_EPISODES}) == 64
    assert [spec.episode_index for spec in FIXED_SEEDED_EPISODES] == list(range(64))
    assert {spec.corpus_version for spec in FIXED_SEEDED_EPISODES} == {
        FIXED_SEEDED_CORPUS_VERSION
    }
    assert FIXED_SEEDED_CORPUS_SHA256 == (
        "ac4efb0beac9e9d14e09cdea7246cbc5c27150479f3ee2a3d93893d314a14ef7"
    )
    assert (
        FIXED_SEEDED_EPISODES[0].game_seed,
        FIXED_SEEDED_EPISODES[0].random_policy_seed,
    ) == ("9CA6BDC0", "16C6FB28D60F79EB")
    assert (
        FIXED_SEEDED_EPISODES[-1].game_seed,
        FIXED_SEEDED_EPISODES[-1].random_policy_seed,
    ) == ("3B8B6C3F", "38CA0EAB146527BA")


def test_env_b0_fixed_schedule_pairs_both_frozen_baselines_over_same_game_seeds():
    calls = []

    def execute(baseline_version, spec, policy_seed):
        calls.append((baseline_version, spec.episode_index, spec.game_seed, policy_seed))
        return _result(baseline_version, spec, policy_seed)

    report = run_fixed_seeded_evaluation(execute)

    assert EVALUATED_BASELINE_VERSIONS == (
        RANDOM_LEGAL_BASELINE_VERSION,
        SYMBOLIC_HEADLESS_BASELINE_VERSION,
    )
    assert report.episode_count == 2 * FIXED_SEEDED_EPISODE_COUNT
    assert [item[2] for item in calls[:64]] == [item[2] for item in calls[64:]]
    assert all(item[3] is not None for item in calls[:64])
    assert all(item[3] is None for item in calls[64:])
    assert tuple(calls) == tuple(
        (baseline, spec.episode_index, spec.game_seed, spec.policy_seed(baseline))
        for baseline in EVALUATED_BASELINE_VERSIONS
        for spec in FIXED_SEEDED_EPISODES
    )


def test_env_b0_result_contract_records_exact_red_white_schema_and_terminal_status():
    spec = FIXED_SEEDED_EPISODES[0]
    result = _result(
        SYMBOLIC_HEADLESS_BASELINE_VERSION,
        spec,
        None,
        status=RunStatus.ANTE_8_WIN,
    )

    assert result.schema_version == FIXED_SEEDED_EVALUATION_SCHEMA
    assert result.corpus_version == FIXED_SEEDED_CORPUS_VERSION
    assert result.corpus_sha256 == FIXED_SEEDED_CORPUS_SHA256
    assert result.observation_version == PUBLIC_OBSERVATION_VERSION
    assert result.action_version == PUBLIC_ACTION_VERSION
    assert (result.deck, result.stake, result.mode) == (
        EVALUATION_DECK,
        EVALUATION_STAKE,
        EVALUATION_MODE,
    )
    assert result.status is RunStatus.ANTE_8_WIN


def test_env_b0_report_json_is_canonical_and_contains_terminal_strings():
    report = _complete_report()

    first = report.to_json()
    second = report.to_json()
    payload = json.loads(first)

    assert first == second
    assert payload["schema_version"] == FIXED_SEEDED_EVALUATION_SCHEMA
    assert payload["corpus_version"] == FIXED_SEEDED_CORPUS_VERSION
    assert payload["corpus_sha256"] == FIXED_SEEDED_CORPUS_SHA256
    assert len(payload["episodes"]) == 128
    assert {episode["status"] for episode in payload["episodes"]} == {"LOSS"}


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"schema_version": "unknown"}, "schema version"),
        ({"corpus_version": "unknown"}, "corpus version"),
        ({"corpus_sha256": "unknown"}, "corpus digest"),
        ({"baseline_version": "unknown"}, "unsupported baseline"),
        ({"observation_version": "unknown"}, "observation version"),
        ({"action_version": "unknown"}, "action version"),
        ({"deck": "BLUE"}, "not Red Deck"),
        ({"game_seed": "DRIFTED"}, "game seed provenance"),
        ({"policy_seed": "DRIFTED"}, "policy seed provenance"),
        ({"status": RunStatus.RUNNING}, "terminal run status"),
        ({"action_count": True}, "action count"),
        ({"action_count": -1}, "action count"),
    ],
)
def test_env_b0_episode_result_fails_closed_on_contract_drift(changes, message):
    spec = FIXED_SEEDED_EPISODES[0]
    result = _result(RANDOM_LEGAL_BASELINE_VERSION, spec, spec.random_policy_seed)

    with pytest.raises(FixedSeededEvaluationError, match=message):
        replace(result, **changes)


def test_env_b0_report_rejects_missing_reordered_or_invalid_episode_evidence():
    report = _complete_report()

    for episodes in (
        report.episodes[:-1],
        tuple(reversed(report.episodes)),
        (object(),),
    ):
        with pytest.raises(FixedSeededEvaluationError):
            FixedSeededEvaluationReport(
                schema_version=FIXED_SEEDED_EVALUATION_SCHEMA,
                corpus_version=FIXED_SEEDED_CORPUS_VERSION,
                corpus_sha256=FIXED_SEEDED_CORPUS_SHA256,
                episodes=episodes,
            )


def test_env_b0_executor_and_unknown_policy_fail_closed_without_rescue():
    with pytest.raises(TypeError, match="executor"):
        run_fixed_seeded_evaluation(None)
    with pytest.raises(TypeError, match="must return"):
        run_fixed_seeded_evaluation(lambda baseline, spec, policy_seed: None)
    with pytest.raises(FixedSeededEvaluationError, match="unsupported baseline"):
        FIXED_SEEDED_EPISODES[0].policy_seed("unknown")
