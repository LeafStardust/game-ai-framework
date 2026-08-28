from types import SimpleNamespace

from games.balatro.shop_observer_latency_diagnostic import _timed_stage


def test_shop_observer_latency_stage_records_without_changing_result():
    owner = SimpleNamespace(_active_shop_latency_profile={})

    result = _timed_stage(owner, "public", lambda: "snapshot")

    assert result == "snapshot"
    assert owner._active_shop_latency_profile["public_calls"] == 1
    assert owner._active_shop_latency_profile["public_seconds"] >= 0.0
