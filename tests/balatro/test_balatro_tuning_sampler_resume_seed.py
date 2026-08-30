from types import SimpleNamespace

import games.balatro.tuning.study as study_module


class _FakeStudy:
    def __init__(self):
        self.user_attrs = {}

    def set_user_attr(self, key, value):
        self.user_attrs[key] = value


def test_create_study_advances_sampler_seed_by_persisted_trial_count(monkeypatch):
    captured = {}
    fake_study = _FakeStudy()

    class _TPESampler:
        def __init__(self, *, seed):
            captured["seed"] = seed

    fake_optuna = SimpleNamespace(
        study=SimpleNamespace(
            get_all_study_summaries=lambda *, storage: [
                SimpleNamespace(study_name="resume-study", n_trials=4)
            ]
        ),
        samplers=SimpleNamespace(TPESampler=_TPESampler),
        create_study=lambda **kwargs: fake_study,
    )
    monkeypatch.setattr(study_module, "_optuna", lambda: fake_optuna)

    result = study_module._create_study(
        name="resume-study",
        storage_url="sqlite:///resume.sqlite3",
        sampler_seed=100,
        attrs={},
    )

    assert result is fake_study
    assert captured["seed"] == 104


def test_create_study_keeps_base_sampler_seed_for_fresh_study(monkeypatch):
    captured = {}
    fake_study = _FakeStudy()

    class _TPESampler:
        def __init__(self, *, seed):
            captured["seed"] = seed

    fake_optuna = SimpleNamespace(
        study=SimpleNamespace(get_all_study_summaries=lambda *, storage: []),
        samplers=SimpleNamespace(TPESampler=_TPESampler),
        create_study=lambda **kwargs: fake_study,
    )
    monkeypatch.setattr(study_module, "_optuna", lambda: fake_optuna)

    study_module._create_study(
        name="fresh-study",
        storage_url="sqlite:///fresh.sqlite3",
        sampler_seed=100,
        attrs={},
    )

    assert captured["seed"] == 100
