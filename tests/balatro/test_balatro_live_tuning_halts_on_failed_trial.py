from types import SimpleNamespace

import balatro_tune_bonds_live as live_tuner


class _FakeStudy:
    def __init__(self):
        self.trials = []
        self.optimize_calls = 0

    def optimize(self, objective, **kwargs):
        self.optimize_calls += 1
        self.trials.append(
            SimpleNamespace(
                number=self.optimize_calls - 1,
                state=SimpleNamespace(name="FAIL"),
                user_attrs={},
            )
        )


def test_live_tuning_stops_after_first_failed_trial(monkeypatch):
    study = _FakeStudy()
    monkeypatch.setattr(live_tuner, "create_live_phase_a_study", lambda config: study)
    monkeypatch.setattr(live_tuner, "enqueue_production_baseline", lambda study: None)
    monkeypatch.setattr(
        live_tuner,
        "make_live_phase_a_objective",
        lambda config, evaluator: object(),
    )

    result = live_tuner.run_live_phase_a(
        SimpleNamespace(),
        object(),
        trials=9,
    )

    assert result is study
    assert study.optimize_calls == 1
    assert len(study.trials) == 1
    assert study.trials[0].state.name == "FAIL"
