import json
from dataclasses import replace

import pytest

from games.balatro.blinds.blind import create_small_blind
from games.balatro.env.evaluation_diagnostics import (
    EVALUATION_DIAGNOSTICS_REPORT_SCHEMA,
    FIXED_EVIDENCE_KIND,
    UNSEEDED_EVIDENCE_KIND,
    EvaluationDiagnosticsError,
    aggregate_evaluation_diagnostics,
    derive_episode_diagnostics,
)
from games.balatro.env.random_baseline import RANDOM_LEGAL_BASELINE_VERSION
from games.balatro.env.seeded_evaluation import (
    FIXED_SEEDED_EVALUATION_SCHEMA,
    FixedSeededEpisodeResult,
    run_fixed_seeded_evaluation,
)
from games.balatro.env.state import EnvStateFrame, RunStatus, TurnOwner
from games.balatro.env.unseeded_evaluation import (
    UNSEEDED_EVALUATION_SCHEMA,
    UnseededEpisodeResult,
    create_unseeded_evaluation_manifest,
    run_unseeded_evaluation,
)
from games.balatro.state import BalatroState


def _frame(*, ante, money, score, status, phase):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.ante = ante
    state.money = money
    state.score = score
    state.phase = phase
    state.blind = create_small_blind(100)
    owner = TurnOwner.TERMINAL if status.terminal else TurnOwner.AGENT
    return EnvStateFrame(state, status=status, owner=owner)


def _fixed_source():
    def execute(baseline, spec, policy_seed):
        status = RunStatus.ANTE_8_WIN if spec.episode_index % 2 == 0 else RunStatus.LOSS
        return FixedSeededEpisodeResult.completed(
            baseline_version=baseline,
            episode_index=spec.episode_index,
            game_seed=spec.game_seed,
            policy_seed=policy_seed,
            status=status,
            action_count=1,
        )

    return run_fixed_seeded_evaluation(execute)


def _unseeded_source():
    manifest = create_unseeded_evaluation_manifest(lambda size: bytes(size))

    def execute(baseline, spec, policy_seed):
        status = RunStatus.ANTE_8_WIN if spec.episode_index % 2 == 0 else RunStatus.LOSS
        return UnseededEpisodeResult.completed(
            manifest,
            baseline_version=baseline,
            episode_index=spec.episode_index,
            game_seed=spec.game_seed,
            policy_seed=policy_seed,
            status=status,
            action_count=1,
        )

    return run_unseeded_evaluation(manifest, execute)


def _diagnostics(source):
    values = []
    for result in source.episodes:
        won = result.status is RunStatus.ANTE_8_WIN
        frames = (
            _frame(
                ante=1,
                money=4,
                score=0,
                status=RunStatus.RUNNING,
                phase="BLIND_SELECT",
            ),
            _frame(
                ante=8 if won else 3,
                money=10 if won else 1,
                score=120 if won else 80,
                status=result.status,
                phase="GAME_OVER",
            ),
        )
        values.append(derive_episode_diagnostics(result, frames))
    return tuple(values)


@pytest.mark.parametrize(
    ("source_factory", "kind", "source_schema"),
    [
        (_fixed_source, FIXED_EVIDENCE_KIND, FIXED_SEEDED_EVALUATION_SCHEMA),
        (_unseeded_source, UNSEEDED_EVIDENCE_KIND, UNSEEDED_EVALUATION_SCHEMA),
    ],
)
def test_env_b0_paired_diagnostic_reports_bind_complete_source_evidence(
    source_factory, kind, source_schema
):
    source = source_factory()
    diagnostics = _diagnostics(source)

    report = aggregate_evaluation_diagnostics(source, diagnostics)

    assert report.schema_version == EVALUATION_DIAGNOSTICS_REPORT_SCHEMA
    assert report.source_schema_version == source_schema
    assert report.evidence_kind == kind
    assert report.episode_count == 128
    assert report.episodes == diagnostics
    assert [summary.baseline_version for summary in report.baselines] == [
        RANDOM_LEGAL_BASELINE_VERSION,
        source.episodes[64].baseline_version,
    ]


def test_env_b0_baseline_summaries_are_exact_descriptive_diagnostics():
    source = _fixed_source()
    report = aggregate_evaluation_diagnostics(source, _diagnostics(source))

    for summary in report.baselines:
        assert summary.episode_count == 64
        assert summary.ante_8_clears == 32
        assert summary.ante_8_clear_rate == 0.5
        assert summary.mean_ante_reached == 5.5
        assert summary.minimum_ante_reached == 3
        assert summary.maximum_ante_reached == 8
        assert summary.mean_terminal_chip_margin == 0.0
        assert summary.mean_terminal_requirement_progress == 1.0
        assert summary.mean_starting_money == 4.0
        assert summary.mean_minimum_money == 2.5
        assert summary.mean_peak_money == 7.0
        assert summary.mean_terminal_money == 5.5
        assert summary.minimum_observed_money == 1
        assert summary.maximum_observed_money == 10


def test_env_b0_diagnostics_report_serialization_is_canonical_and_auditable():
    source = _unseeded_source()
    report = aggregate_evaluation_diagnostics(source, _diagnostics(source))
    payload = json.loads(report.to_json())

    assert report.to_json() == report.to_json()
    assert payload["evidence_sha256"] == source.manifest.manifest_sha256
    assert len(payload["episodes"]) == 128
    assert len(payload["baselines"]) == 2


def test_env_b0_aggregation_rejects_missing_reordered_or_wrong_source_diagnostics():
    fixed = _fixed_source()
    unseeded = _unseeded_source()
    diagnostics = _diagnostics(fixed)

    with pytest.raises(EvaluationDiagnosticsError, match="exactly one"):
        aggregate_evaluation_diagnostics(fixed, diagnostics[:-1])
    with pytest.raises(EvaluationDiagnosticsError, match="does not match"):
        aggregate_evaluation_diagnostics(fixed, tuple(reversed(diagnostics)))
    with pytest.raises(EvaluationDiagnosticsError, match="does not match"):
        aggregate_evaluation_diagnostics(unseeded, diagnostics)
    with pytest.raises(TypeError, match="source"):
        aggregate_evaluation_diagnostics(object(), diagnostics)


def test_env_b0_aggregate_report_rejects_summary_tampering():
    source = _fixed_source()
    report = aggregate_evaluation_diagnostics(source, _diagnostics(source))
    tampered = replace(report.baselines[0], ante_8_clear_rate=1.0)

    with pytest.raises(EvaluationDiagnosticsError, match="summaries"):
        replace(report, baselines=(tampered, report.baselines[1]))
