from types import SimpleNamespace

import balatro_tune_bonds_live as cli


def test_baseline_only_refuses_reused_study_before_evaluator(monkeypatch, tmp_path, capsys):
    constructed = []
    monkeypatch.setattr(cli, "_repository_sha", lambda explicit: "abc123")
    monkeypatch.setattr(
        cli,
        "validate_live_tuning_preflight",
        lambda **kwargs: SimpleNamespace(
            phase="BLIND_SELECT",
            ante=1,
            deck="RED",
            stake="WHITE",
            bridge_version="1",
            bridge_revision="test",
            achievement_gate="UNSET",
        ),
    )
    monkeypatch.setattr(
        cli,
        "create_live_phase_a_study",
        lambda config: SimpleNamespace(trials=[SimpleNamespace(number=0)]),
    )

    class _Evaluator:
        def __init__(self, **kwargs):
            constructed.append(kwargs)

    monkeypatch.setattr(cli, "AuthoritativeLiveBatchEvaluator", _Evaluator)
    monkeypatch.setattr(
        "sys.argv",
        [
            "balatro_tune_bonds_live.py",
            "--study", "existing",
            "--storage", str(tmp_path / "study.sqlite3"),
            "--baseline-only",
        ],
    )

    assert cli.main() == 2
    assert constructed == []
    assert "requires a fresh study" in capsys.readouterr().out


def test_baseline_only_runs_one_trial_and_requires_baseline_tag(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "_repository_sha", lambda explicit: "abc123")
    monkeypatch.setattr(
        cli,
        "validate_live_tuning_preflight",
        lambda **kwargs: SimpleNamespace(
            phase="BLIND_SELECT",
            ante=1,
            deck="RED",
            stake="WHITE",
            bridge_version="1",
            bridge_revision="test",
            achievement_gate="UNSET",
        ),
    )
    monkeypatch.setattr(
        cli,
        "create_live_phase_a_study",
        lambda config: SimpleNamespace(trials=[]),
    )
    monkeypatch.setattr(cli, "AuthoritativeLiveBatchEvaluator", lambda **kwargs: object())

    latest = SimpleNamespace(
        state=SimpleNamespace(name="COMPLETE"),
        user_attrs={
            "production_baseline": True,
            "session_id": "session-1",
            "won": False,
        },
    )
    study = SimpleNamespace(
        study_name="fresh",
        trials=[latest],
        best_value=12.5,
    )
    calls = []
    monkeypatch.setattr(
        cli,
        "run_live_phase_a",
        lambda config, evaluator, *, trials, timeout_seconds: calls.append(trials) or study,
    )
    monkeypatch.setattr(cli, "write_study_report", lambda study, path: path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "balatro_tune_bonds_live.py",
            "--study", "fresh",
            "--storage", str(tmp_path / "study.sqlite3"),
            "--report", str(tmp_path / "report.json"),
            "--baseline-only",
        ],
    )

    assert cli.main() == 0
    assert calls == [1]
    output = capsys.readouterr().out
    assert "Latest production baseline -> True" in output
    assert "inspect baseline report" in output


def test_repository_sha_rejects_dirty_worktree(monkeypatch):
    def fake_git(*args):
        if args == ("status", "--porcelain"):
            return " M file.py"
        raise AssertionError(args)

    monkeypatch.setattr(cli, "_git", fake_git)
    try:
        cli._repository_sha(None)
    except RuntimeError as error:
        assert "clean worktree" in str(error)
    else:
        raise AssertionError("dirty worktree should be rejected")
