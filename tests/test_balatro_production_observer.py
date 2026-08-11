from games.balatro.live.external.production_observer import ProductionBalatroObserver
from games.balatro.live.external.state_observer_factory import create_balatro_state_observer
from games.balatro.live.protocol import LiveBalatroSnapshot


class _Observer:
    def __init__(self):
        self.closed = False

    def observe(self):
        return LiveBalatroSnapshot(
            sequence=7,
            phase="SELECTING_HAND",
            state_complete=True,
            payload={
                "hand": {"cards": [{"live_id": 5.0}, {"live_id": "card-x"}]},
                "cards": {"cards": [{"live_id": 31.0}]},
                "jokers": {"cards": [{"live_id": 44.0}]},
                "hidden_rng_exposed": False,
                "hidden_draw_order_exposed": False,
            },
        )

    def is_connected(self):
        return True

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def test_production_observer_normalizes_integral_live_ids():
    raw = _Observer()
    observer = ProductionBalatroObserver(raw)

    snapshot = observer.observe()

    assert snapshot.sequence == 7
    assert snapshot.payload["hand"]["cards"][0]["live_id"] == 5
    assert isinstance(snapshot.payload["hand"]["cards"][0]["live_id"], int)
    assert snapshot.payload["hand"]["cards"][1]["live_id"] == "card-x"
    assert snapshot.payload["cards"]["cards"][0]["live_id"] == 31
    assert snapshot.payload["jokers"]["cards"][0]["live_id"] == 44
    assert snapshot.payload["hidden_rng_exposed"] is False
    assert snapshot.payload["hidden_draw_order_exposed"] is False


def test_production_observer_delegates_connection_and_close():
    raw = _Observer()
    observer = ProductionBalatroObserver(raw)

    assert observer.is_connected() is True
    observer.close()
    assert raw.closed is True


def test_factory_defaults_to_production_live_memory_observer():
    observer = create_balatro_state_observer()
    try:
        assert isinstance(observer, ProductionBalatroObserver)
    finally:
        observer.close()
