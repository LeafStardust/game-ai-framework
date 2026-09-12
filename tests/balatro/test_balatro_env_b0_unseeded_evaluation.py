import json
from dataclasses import replace

import pytest

from games.balatro.env.random_baseline import RANDOM_LEGAL_BASELINE_VERSION
from games.balatro.env.seeded_evaluation import (
    EVALUATED_BASELINE_VERSIONS,
    FIXED_SEEDED_EPISODES,
)
from games.balatro.env.state import RunStatus
from games.balatro.env.symbolic_baseline import SYMBOLIC_HEADLESS_BASELINE_VERSION
from games.balatro.env.unseeded_evaluation import (
    UNSEEDED_EPISODE_COUNT,
    UNSEEDED_EVALUATION_SCHEMA,
    UNSEEDED_MANIFEST_SCHEMA,
    UnseededEpisodeResult,
    UnseededEvaluationError,
    UnseededEvaluationManifest,
    UnseededEvaluationReport,
    create_unseeded_evaluation_manifest,
    run_unseeded_evaluation,
)


def _manifest(byte=0):
    return create_unseeded_evaluation_manifest(lambda size: bytes([byte]) * size)


def _result(manifest, baseline, spec, policy_seed):
    return UnseededEpisodeResult.completed(
        manifest,
        baseline_version=baseline,
        episode_index=spec.episode_index,
        game_seed=spec.game_seed,
        policy_seed=policy_seed,
        status=RunStatus.LOSS,
        action_count=spec.episode_index,
    )


def _report(manifest=None):
    manifest = manifest or _manifest()
    return run_unseeded_evaluation(
        manifest,
        lambda baseline, spec, policy_seed: _result(
            manifest, baseline, spec, policy_seed
        ),
    )


def test_env_b0_unseeded_manifest_is_replayable_unique_separate_and_pinned():
    manifest = _manifest()
    replay = _manifest()
    fixed = {spec.game_seed for spec in FIXED_SEEDED_EPISODES}

    assert manifest == replay
    assert manifest.schema_version == UNSEEDED_MANIFEST_SCHEMA
    assert manifest.entropy_hex == "00" * 32
    assert manifest.manifest_sha256 == (
        "b42d0280c551622ed63f1a4d0e1cc89f7eb41164459cb1e9699020d6bca6fd37"
    )
    assert len(manifest.episodes) == UNSEEDED_EPISODE_COUNT == 64
    assert len({spec.game_seed for spec in manifest.episodes}) == 64
    assert not fixed.intersection(spec.game_seed for spec in manifest.episodes)
    assert (manifest.episodes[0].game_seed, manifest.episodes[0].random_policy_seed) == (
        "A1F73FA0",
        "12752684FE2F914A",
    )
    assert (manifest.episodes[-1].game_seed, manifest.episodes[-1].random_policy_seed) == (
        "06574AD8",
        "B69FFDB2DDF77492",
    )


def test_env_b0_distinct_entropy_creates_distinct_unseeded_manifests():
    first = _manifest(1)
    second = _manifest(2)

    assert first.manifest_sha256 != second.manifest_sha256
    assert {item.game_seed for item in first.episodes}.isdisjoint(
        item.game_seed for item in second.episodes
    )


def test_env_b0_unseeded_schedule_pairs_both_baselines_and_records_provenance():
    manifest = _manifest()
    calls = []

    def execute(baseline, spec, policy_seed):
        calls.append((baseline, spec.episode_index, spec.game_seed, policy_seed))
        return _result(manifest, baseline, spec, policy_seed)

    report = run_unseeded_evaluation(manifest, execute)

    assert report.episode_count == 128
    assert [item[2] for item in calls[:64]] == [item[2] for item in calls[64:]]
    assert all(item[3] is not None for item in calls[:64])
    assert all(item[3] is None for item in calls[64:])
    assert tuple(calls) == tuple(
        (baseline, spec.episode_index, spec.game_seed, spec.policy_seed(baseline))
        for baseline in EVALUATED_BASELINE_VERSIONS
        for spec in manifest.episodes
    )


def test_env_b0_unseeded_report_json_keeps_manifest_and_results_separate():
    report = _report()
    payload = json.loads(report.to_json())

    assert payload["schema_version"] == UNSEEDED_EVALUATION_SCHEMA
    assert payload["manifest"]["schema_version"] == UNSEEDED_MANIFEST_SCHEMA
    assert payload["manifest"]["manifest_sha256"] == report.manifest.manifest_sha256
    assert len(payload["episodes"]) == 128
    assert {item["status"] for item in payload["episodes"]} == {"LOSS"}


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": "unknown"},
        {"entropy_hex": "00"},
        {"entropy_hex": "GG" * 32},
        {"manifest_sha256": "0" * 64},
        {"episodes": ()},
    ],
)
def test_env_b0_unseeded_manifest_tampering_fails_closed(change):
    with pytest.raises(UnseededEvaluationError):
        replace(_manifest(), **change)


def test_env_b0_unseeded_report_rejects_missing_reordered_and_drifted_results():
    report = _report()

    for episodes in (
        report.episodes[:-1],
        tuple(reversed(report.episodes)),
    ):
        with pytest.raises(UnseededEvaluationError):
            UnseededEvaluationReport(
                schema_version=UNSEEDED_EVALUATION_SCHEMA,
                manifest=report.manifest,
                episodes=episodes,
            )


def test_env_b0_unseeded_nonterminal_and_executor_fail_closed_without_rescue():
    manifest = _manifest()
    spec = manifest.episodes[0]
    result = _result(manifest, RANDOM_LEGAL_BASELINE_VERSION, spec, spec.random_policy_seed)

    with pytest.raises(UnseededEvaluationError, match="terminal"):
        replace(result, status=RunStatus.RUNNING)
    with pytest.raises(UnseededEvaluationError, match="game seed provenance"):
        replace(result, game_seed="DRIFTED")
    with pytest.raises(UnseededEvaluationError, match="policy seed provenance"):
        replace(result, policy_seed="DRIFTED")
    with pytest.raises(UnseededEvaluationError, match="manifest digest"):
        replace(result, manifest_sha256="0" * 64)
    with pytest.raises(TypeError, match="manifest"):
        run_unseeded_evaluation(None, lambda *args: None)
    with pytest.raises(TypeError, match="executor"):
        run_unseeded_evaluation(manifest, None)
    with pytest.raises(TypeError, match="must return"):
        run_unseeded_evaluation(manifest, lambda *args: None)
    with pytest.raises(UnseededEvaluationError, match="unsupported baseline"):
        spec.policy_seed("unknown")
    assert spec.policy_seed(SYMBOLIC_HEADLESS_BASELINE_VERSION) is None
