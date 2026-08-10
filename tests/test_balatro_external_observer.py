import pytest

from games.balatro.live.external import (
    BalatroFrame,
    BalatroWindow,
    ExternalBalatroObserver,
    PhaseDetection,
    WindowRect,
)


class Capture:

    def __init__(self, frame):
        self.frame = frame
        self.closed = False

    def capture(self):
        return self.frame

    def close(self):
        self.closed = True


class Recognizer:

    def __init__(self, phases):
        self.phases = iter(phases)

    def detect(self, frame):
        phase = next(self.phases)
        return PhaseDetection(phase, 1.0, 0.0)


def _frame():
    return BalatroFrame(
        sequence=1,
        timestamp=0.0,
        window=BalatroWindow(
            handle=1,
            title="Balatro",
            client_rect=WindowRect(0, 0, 20, 10),
        ),
        width=20,
        height=10,
        bgra=bytes(20 * 10 * 4),
    )


def test_external_observer_returns_frame_and_visual_phase():
    observer = ExternalBalatroObserver(
        capture=Capture(_frame()),
        recognizer=Recognizer(["SHOP"]),
    )

    observation = observer.observe()

    assert observation.frame.sequence == 1
    assert observation.phase.phase == "SHOP"


def test_external_observer_waits_for_target_phase():
    observer = ExternalBalatroObserver(
        capture=Capture(_frame()),
        recognizer=Recognizer(["UNKNOWN", "BLIND_SELECT"]),
    )

    observation = observer.wait_for_phase(
        "BLIND_SELECT",
        timeout=1,
        poll_interval=0,
    )

    assert observation.phase.phase == "BLIND_SELECT"


def test_external_observer_times_out_when_phase_never_arrives():
    class UnknownRecognizer:
        def detect(self, frame):
            return PhaseDetection("UNKNOWN", 0.0, 1.0)

    observer = ExternalBalatroObserver(
        capture=Capture(_frame()),
        recognizer=UnknownRecognizer(),
    )

    with pytest.raises(TimeoutError):
        observer.wait_for_phase(
            "SHOP",
            timeout=0,
            poll_interval=0,
        )


def test_external_observer_closes_capture():
    capture = Capture(_frame())
    observer = ExternalBalatroObserver(
        capture=capture,
        recognizer=Recognizer(["SHOP"]),
    )

    observer.close()

    assert capture.closed is True
