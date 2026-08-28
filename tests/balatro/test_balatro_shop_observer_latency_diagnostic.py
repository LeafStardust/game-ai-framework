from types import SimpleNamespace

from games.balatro.shop_observer_latency_diagnostic import (
    _timed_stage,
    shop_decision_latency_note,
)


def test_shop_observer_latency_stage_records_without_changing_result():
    owner = SimpleNamespace(_active_shop_latency_profile={})

    result = _timed_stage(owner, "public", lambda: "snapshot")

    assert result == "snapshot"
    assert owner._active_shop_latency_profile["public_calls"] == 1
    assert owner._active_shop_latency_profile["public_seconds"] >= 0.0


def test_shop_decision_latency_note_separates_runner_components():
    runner = SimpleNamespace(
        last_observation_seconds=0.25,
        last_translation_seconds=0.125,
        last_policy_seconds=3.5,
    )

    note = shop_decision_latency_note(runner, 3.875)

    assert note == (
        "shop_decision_latency=total=3.875s "
        "observation=0.250s translation=0.125s policy=3.500s"
    )
