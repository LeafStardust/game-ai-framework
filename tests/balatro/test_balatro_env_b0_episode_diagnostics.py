from dataclasses import replace

import pytest

from games.balatro.blinds.blind import create_small_blind
from games.balatro.env.evaluation_diagnostics import (
    EVALUATION_DIAGNOSTICS_SCHEMA,
    FIXED_EVIDENCE_KIND,
    UNSEEDED_EVIDENCE_KIND,
    EvaluationDiagnosticsError,
    derive_episode_diagnostics,
)
from games.balatro.env.random_baseline import RANDOM_LEGAL_BASELINE_VERSION
from games.balatro.env.seeded_evaluation import (
    FIXED_SEEDED_EPISODES,
    FixedSeededEpisodeResult,
)
from games.balatro.env.state import EnvStateFrame, RunStatus, TurnOwner
from games.balatro.env.symbolic_baseline import SYMBOLIC_HEADLESS_BASELINE_VERSION
from games.balatro.env.unseeded_evaluation import (
    UnseededEpisodeResult,
    create_unseeded_evaluation_manifest,
)
from games.balatro.state import BalatroState


def _frame(*, ante, money, score, status=RunStatus.RUNNING, phase="SELECTING_HAND"):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.ante = ante
    state.money = money
    state.score = score
    state.phase = phase
    state.blind = create_small_blind(300)
    owner = TurnOwner.TERMINAL if status.terminal else TurnOwner.AGENT
    return EnvStateFrame(state, status=status, owner=owner)


def _fixed_result(*, status=RunStatus.LOSS, action_count=2):
    spec = FIXED_SEEDED_EPISODES[0]
    return FixedSeededEpisodeResult.completed(
        baseline_version=RANDOM_LEGAL_BASELINE_VERSION,
        episode_index=spec.episode_index,
        game_seed=spec.game_seed,
        policy_seed=spec.random_policy_seed,
        status=status,
        action_count=action_count,
    )


def _unseeded_result(*, status=RunStatus.ANTE_8_WIN, action_count=2):
    manifest = create_unseeded_evaluation_manifest(lambda size: bytes(size))
    spec = manifest.episodes[0]
    return UnseededEpisodeResult.completed(
        manifest,
        baseline_version=SYMBOLIC_HEADLESS_BASELINE_VERSION,
        episode_index=spec.episode_index,
        game_seed=spec.game_seed,
        policy_seed=None,
        status=status,
        action_count=action_count,
    )


def _loss_trace():
    return (
        _frame(ante=1, money=4, score=0, phase="BLIND_SELECT"),
        _frame(ante=2, money=1, score=120),
        _frame(ante=3, money=7, score=240, status=RunStatus.LOSS, phase="GAME_OVER"),
    )


def _win_trace():
    return (
        _frame(ante=1, money=4, score=0, phase="BLIND_SELECT"),
        _frame(ante=7, money=25, score=150),
        _frame(
            ante=8,
            money=12,
            score=360,
            status=RunStatus.ANTE_8_WIN,
            phase="GAME_OVER",
        ),
    )


def test_env_b0_fixed_loss_diagnostics_use_only_authoritative_trace_values():
    diagnostics = derive_episode_diagnostics(_fixed_result(), _loss_trace())

    assert diagnostics.schema_version == EVALUATION_DIAGNOSTICS_SCHEMA
    assert diagnostics.evidence_kind == FIXED_EVIDENCE_KIND
    assert diagnostics.ante_reached == 3
    assert diagnostics.ante_8_cleared is False
    assert diagnostics.terminal_blind_score == 240.0
    assert diagnostics.terminal_blind_requirement == 300.0
    assert diagnostics.terminal_chip_margin == -60.0
    assert diagnostics.terminal_requirement_progress == 0.8
    assert (
        diagnostics.starting_money,
        diagnostics.minimum_money,
        diagnostics.peak_money,
        diagnostics.terminal_money,
    ) == (4, 1, 7, 7)


def test_env_b0_unseeded_win_diagnostics_bind_manifest_and_ante_8_clear():
    result = _unseeded_result()
    diagnostics = derive_episode_diagnostics(result, _win_trace())

    assert diagnostics.evidence_kind == UNSEEDED_EVIDENCE_KIND
    assert diagnostics.evidence_sha256 == result.manifest_sha256
    assert diagnostics.baseline_version == SYMBOLIC_HEADLESS_BASELINE_VERSION
    assert diagnostics.game_seed == result.game_seed
    assert diagnostics.ante_reached == 8
    assert diagnostics.ante_8_cleared is True
    assert diagnostics.terminal_chip_margin == 60.0
    assert diagnostics.terminal_requirement_progress == 1.2
    assert diagnostics.to_json() == diagnostics.to_json()
    assert '"status":"ANTE_8_WIN"' in diagnostics.to_json()


@pytest.mark.parametrize(
    ("frames", "message"),
    [
        ((), "at least two"),
        ((_loss_trace()[0],), "at least two"),
        ((_frame(ante=1, money=4, score=0), _loss_trace()[-1]), "reset boundary"),
        ((_loss_trace()[0], _loss_trace()[1]), "terminate exactly once"),
        (
            (_loss_trace()[0], _loss_trace()[-1], _loss_trace()[1]),
            "terminate exactly once",
        ),
    ],
)
def test_env_b0_diagnostics_require_complete_reset_to_terminal_trace(frames, message):
    with pytest.raises(EvaluationDiagnosticsError, match=message):
        derive_episode_diagnostics(_fixed_result(action_count=0), frames)


def test_env_b0_diagnostics_fail_closed_on_status_identity_and_progress_drift():
    result = _fixed_result(action_count=0)
    wrong_status = (*_loss_trace()[:-1], _win_trace()[-1])
    wrong_deck = _frame(ante=2, money=4, score=100)
    wrong_deck.state.deck_name = "BLUE"
    decreasing = (_loss_trace()[0], _frame(ante=2, money=4, score=100), _loss_trace()[-1])
    decreasing[-1].state.ante = 1

    with pytest.raises(EvaluationDiagnosticsError, match="status mismatches"):
        derive_episode_diagnostics(result, wrong_status)
    with pytest.raises(EvaluationDiagnosticsError, match="not Red Deck"):
        derive_episode_diagnostics(result, (_loss_trace()[0], wrong_deck, _loss_trace()[-1]))
    with pytest.raises(EvaluationDiagnosticsError, match="cannot decrease"):
        derive_episode_diagnostics(result, decreasing)


def test_env_b0_diagnostics_reject_missing_or_contradictory_survival_evidence():
    result = _fixed_result(action_count=0)
    missing_blind = _loss_trace()[-1]
    missing_blind.state.blind = None
    cleared_loss = _loss_trace()[-1]
    cleared_loss.state.score = 300

    with pytest.raises(EvaluationDiagnosticsError, match="no authoritative blind"):
        derive_episode_diagnostics(result, (*_loss_trace()[:-1], missing_blind))
    with pytest.raises(EvaluationDiagnosticsError, match="loss already satisfies"):
        derive_episode_diagnostics(result, (*_loss_trace()[:-1], cleared_loss))
    with pytest.raises(EvaluationDiagnosticsError, match="exceeds recorded transitions"):
        derive_episode_diagnostics(_fixed_result(action_count=3), _loss_trace())


def test_env_b0_diagnostic_record_rejects_derived_field_tampering():
    diagnostics = derive_episode_diagnostics(_fixed_result(), _loss_trace())

    with pytest.raises(EvaluationDiagnosticsError, match="inconsistent"):
        replace(diagnostics, terminal_chip_margin=0.0)
    with pytest.raises(EvaluationDiagnosticsError, match="contradicts"):
        replace(diagnostics, ante_8_cleared=True)
    with pytest.raises(EvaluationDiagnosticsError, match="digest"):
        replace(diagnostics, evidence_sha256="z" * 64)
