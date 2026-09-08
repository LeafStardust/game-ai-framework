from types import SimpleNamespace

import balatro_tune_bonds_live as cli


class _FakeTrial:
    def __init__(self):
        self.state = SimpleNamespace(name="COMPLETE")
        self.user_attrs = {
            "production_baseline": False,
            "won": False,
            "session_id": "test-session",
        }


class _FakeStudy:
    def __init__(self):
        self.study_name = "sampler-lifecycle"
        self.trials = []
        self.best_value = 1.0
        self.optimize_calls = 0

    def optimize(self, objective, *, n_trials, timeout, gc_after_trial, catch):
        assert n_trials == 1
        self.optimize_calls += 1
        self.trials.append(_FakeTrial())


def test_live_cli_reuses_one_study_sampler_across_requested_trials(monkeypatch, tmp_path):
    args = SimpleNamespace(
        study="sampler-lifecycle",
        storage=tmp_path / "study.sqlite3",
        report=tmp_path / "report.json",
        repo_sha="deadbeef",
        trials=5,
        attempts_per_trial=3,
        timeout_seconds=None,
        sampler_seed=20260823,
        deck="RED",
        stake="WHITE",
        baseline_only=False,
        run_log_directory=tmp_path / "runs",
        session_directory=tmp_path / "sessions",
        control_directory=tmp_path / "control",
    )
    monkeypatch.setattr(
        cli,
        "build_parser",
        lambda: SimpleNamespace(parse_args=lambda: args),
    )
    monkeypatch.setattr(
        cli,
        "validate_live_tuning_preflight",
        lambda **kwargs: SimpleNamespace(
            phase="BLIND_SELECT",
            ante=1,
            deck="RED",
            stake="WHITE",
            bridge_version=1,
            bridge_revision=9,
            achievement_gate="ENABLED",
        ),
    )

    study = _FakeStudy()
    create_calls = []

    def create(config):
        create_calls.append(config)
        return study

    monkeypatch.setattr(cli, "create_live_phase_a_study", create)
    monkeypatch.setattr(cli, "enqueue_production_baseline", lambda study: None)
    monkeypatch.setattr(
        cli,
        "AuthoritativeLiveBatchEvaluator",
        lambda **kwargs: SimpleNamespace(),
    )
    objective = object()
    monkeypatch.setattr(cli, "make_live_phase_a_objective", lambda config, evaluator: objective)
    monkeypatch.setattr(cli, "write_study_report", lambda study, path: path)

    result = cli.main()

    assert result == 0
    assert len(create_calls) == 1
    assert study.optimize_calls == 5
    assert len(study.trials) == 5
