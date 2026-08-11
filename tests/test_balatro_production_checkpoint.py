from games.balatro.live.external.production_observer import ProductionBalatroObserver
from games.balatro.live.protocol import LiveBalatroSnapshot


class _MovingObserver:
    def __init__(self):
        self.x = 1.0
        self.score = 0

    def observe(self):
        return LiveBalatroSnapshot(
            sequence=1,
            phase="SELECTING_HAND",
            state_complete=True,
            payload={
                "score": self.score,
                "hand": {
                    "cards": [
                        {
                            "live_id": 5.0,
                            "value": {"rank": "Ace", "suit": "Spades"},
                            "ui": {"x": self.x, "y": 2.0, "w": 1.0, "h": 1.0},
                        }
                    ]
                },
                "hidden_rng_exposed": False,
                "hidden_draw_order_exposed": False,
            },
        )

    def is_connected(self):
        return True

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


def test_ui_motion_does_not_advance_production_sequence():
    raw = _MovingObserver()
    observer = ProductionBalatroObserver(raw)

    first = observer.observe()
    raw.x = 9.0
    second = observer.observe()

    assert first.sequence == 1
    assert second.sequence == 1
    assert second.payload["hand"]["cards"][0]["ui"]["x"] == 9.0


def test_logical_change_advances_production_sequence():
    raw = _MovingObserver()
    observer = ProductionBalatroObserver(raw)

    first = observer.observe()
    raw.score = 120
    second = observer.observe()

    assert first.sequence == 1
    assert second.sequence == 2
