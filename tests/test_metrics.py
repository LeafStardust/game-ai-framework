from framework.metrics.metrics import Metrics


def test_metrics_record_and_get():

    metrics = Metrics()

    metrics.record(
        "reward",
        1.0
    )

    assert metrics.get("reward") == 1.0


def test_metrics_missing_value():

    metrics = Metrics()

    assert metrics.get("unknown") is None