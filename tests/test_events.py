from framework.events.event import EventManager


def test_event_subscription_and_emit():

    events = EventManager()
    received = []

    def callback(data):
        received.append(data)

    events.subscribe(
        "test",
        callback
    )

    events.emit(
        "test",
        123
    )

    assert received == [123]


def test_emit_without_listener():

    events = EventManager()

    events.emit(
        "unknown",
        "data"
    )