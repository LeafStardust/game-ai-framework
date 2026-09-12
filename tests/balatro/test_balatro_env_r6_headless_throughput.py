import json

import pytest

from games.balatro.env import performance


def test_env_r6_headless_baseline_pins_workload_and_report(monkeypatch):
    calls = []
    canonical_step = performance.start_pristine_first_small_blind

    def counted_step(run):
        calls.append(run)
        return canonical_step(run)

    monkeypatch.setattr(performance, "start_pristine_first_small_blind", counted_step)
    clock_values = iter((10.0, 12.5))

    report = performance.measure_headless_steps_per_second(
        warmup_steps=2,
        measured_steps=5,
        clock=lambda: next(clock_values),
    )

    assert len(calls) == 7
    assert len({id(run) for run in calls}) == 1
    assert calls[0].public.phase == "BLIND_SELECT"
    assert report.as_dict() == {
        "schema": "balatro-r6-headless-throughput-v1",
        "workload": "red-white-pristine-small-blind-start-v1",
        "warmup_steps": 2,
        "measured_steps": 5,
        "elapsed_seconds": 2.5,
        "steps_per_second": 2.0,
    }
    assert json.loads(report.to_json()) == report.as_dict()


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"warmup_steps": -1}, "warmup_steps"),
        ({"warmup_steps": True}, "warmup_steps"),
        ({"measured_steps": 0}, "measured_steps"),
        ({"measured_steps": 1.5}, "measured_steps"),
    ],
)
def test_env_r6_headless_baseline_rejects_invalid_counts(kwargs, match):
    with pytest.raises(ValueError, match=match):
        performance.measure_headless_steps_per_second(**kwargs)


def test_env_r6_headless_baseline_rejects_invalid_elapsed_time():
    clock_values = iter((3.0, 3.0))

    with pytest.raises(RuntimeError, match="positive finite elapsed"):
        performance.measure_headless_steps_per_second(
            warmup_steps=0,
            measured_steps=1,
            clock=lambda: next(clock_values),
        )


def test_env_r6_headless_baseline_cli_emits_one_machine_readable_report(
    monkeypatch,
    capsys,
):
    received = {}
    expected = performance.HeadlessThroughputReport(
        schema=performance.HEADLESS_THROUGHPUT_SCHEMA,
        workload=performance.HEADLESS_STEPS_WORKLOAD,
        warmup_steps=3,
        measured_steps=7,
        elapsed_seconds=0.5,
        steps_per_second=14.0,
    )

    def fake_measurement(**kwargs):
        received.update(kwargs)
        return expected

    monkeypatch.setattr(
        performance,
        "measure_headless_steps_per_second",
        fake_measurement,
    )

    assert performance.main(["--warmup-steps", "3", "--measured-steps", "7"]) == 0
    assert received == {"warmup_steps": 3, "measured_steps": 7}
    assert json.loads(capsys.readouterr().out) == expected.as_dict()
