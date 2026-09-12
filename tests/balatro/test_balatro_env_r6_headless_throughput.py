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


def test_env_r6_complete_run_workload_reaches_exact_terminal_loss(monkeypatch):
    plays = []
    canonical_play = performance.apply_supported_ordinary_play

    def counted_play(run, indices):
        plays.append((run.public.phase, tuple(indices)))
        return canonical_play(run, indices)

    monkeypatch.setattr(performance, "apply_supported_ordinary_play", counted_play)

    result = performance.run_fixed_red_white_episode()

    assert plays == [("SELECTING_HAND", (0,))] * 4
    assert result.public.deck_name == "RED"
    assert result.public.stake_name == "WHITE"
    assert result.public.ante == 1
    assert result.public.round == 1
    assert result.public.phase == "GAME_OVER"
    assert result.public.hands_remaining == 0
    assert result.public.score == 56
    assert result.public.blind.requirement == 300


def test_env_r6_complete_runs_baseline_pins_workload_and_report(monkeypatch):
    episodes = []
    canonical_episode = performance.run_fixed_red_white_episode

    def counted_episode():
        result = canonical_episode()
        episodes.append(result)
        return result

    monkeypatch.setattr(performance, "run_fixed_red_white_episode", counted_episode)
    clock_values = iter((20.0, 22.5))

    report = performance.measure_complete_red_white_runs_per_minute(
        warmup_runs=2,
        measured_runs=5,
        clock=lambda: next(clock_values),
    )

    assert len(episodes) == 7
    assert all(run.public.phase == "GAME_OVER" for run in episodes)
    assert report.as_dict() == {
        "schema": "balatro-r6-complete-runs-throughput-v1",
        "workload": "red-white-first-small-blind-single-card-loss-v1",
        "warmup_runs": 2,
        "measured_runs": 5,
        "completed_runs": 5,
        "elapsed_seconds": 2.5,
        "runs_per_minute": 120.0,
    }
    assert json.loads(report.to_json()) == report.as_dict()


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"warmup_runs": -1}, "warmup_runs"),
        ({"warmup_runs": True}, "warmup_runs"),
        ({"measured_runs": 0}, "measured_runs"),
        ({"measured_runs": 1.5}, "measured_runs"),
    ],
)
def test_env_r6_complete_runs_baseline_rejects_invalid_counts(kwargs, match):
    with pytest.raises(ValueError, match=match):
        performance.measure_complete_red_white_runs_per_minute(**kwargs)


def test_env_r6_complete_runs_baseline_rejects_invalid_elapsed_time():
    clock_values = iter((4.0, 4.0))

    with pytest.raises(RuntimeError, match="positive finite elapsed"):
        performance.measure_complete_red_white_runs_per_minute(
            warmup_runs=0,
            measured_runs=1,
            clock=lambda: next(clock_values),
        )


def test_env_r6_complete_runs_baseline_counts_only_exact_terminal_episodes(monkeypatch):
    monkeypatch.setattr(
        performance,
        "run_fixed_red_white_episode",
        performance._pristine_small_blind_template,
    )

    with pytest.raises(RuntimeError, match="exact terminal loss"):
        performance.measure_complete_red_white_runs_per_minute(
            warmup_runs=0,
            measured_runs=1,
        )


def test_env_r6_complete_runs_cli_emits_one_machine_readable_report(
    monkeypatch,
    capsys,
):
    received = {}
    expected = performance.CompleteRunsThroughputReport(
        schema=performance.COMPLETE_RUNS_THROUGHPUT_SCHEMA,
        workload=performance.COMPLETE_RUNS_WORKLOAD,
        warmup_runs=4,
        measured_runs=9,
        completed_runs=9,
        elapsed_seconds=3.0,
        runs_per_minute=180.0,
    )

    def fake_measurement(**kwargs):
        received.update(kwargs)
        return expected

    monkeypatch.setattr(
        performance,
        "measure_complete_red_white_runs_per_minute",
        fake_measurement,
    )

    assert performance.main(
        [
            "--metric",
            "runs",
            "--warmup-runs",
            "4",
            "--measured-runs",
            "9",
        ]
    ) == 0
    assert received == {"warmup_runs": 4, "measured_runs": 9}
    assert json.loads(capsys.readouterr().out) == expected.as_dict()
