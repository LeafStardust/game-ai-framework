from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from .capture import BalatroFrame, BalatroScreenCapture
from .phase_templates import load_phase_templates
from .vision import (
    BalatroVisualPhaseRecognizer,
    PhaseDetection,
)


@dataclass(frozen=True)
class ExternalBalatroObservation:
    frame: BalatroFrame
    phase: PhaseDetection


class ExternalBalatroObserver:
    """Captures the visible Steam game and interprets its broad UI phase."""

    def __init__(
        self,
        capture: BalatroScreenCapture | None = None,
        recognizer: BalatroVisualPhaseRecognizer | None = None,
    ):
        self.capture = capture or BalatroScreenCapture()
        self.recognizer = recognizer or BalatroVisualPhaseRecognizer()

    @classmethod
    def from_template_file(
        cls,
        path: str | Path,
        *,
        capture: BalatroScreenCapture | None = None,
    ) -> ExternalBalatroObserver:
        return cls(
            capture=capture,
            recognizer=BalatroVisualPhaseRecognizer(
                load_phase_templates(path)
            ),
        )

    def observe(self) -> ExternalBalatroObservation:
        frame = self.capture.capture()
        return ExternalBalatroObservation(
            frame=frame,
            phase=self.recognizer.detect(frame),
        )

    def wait_for_phase(
        self,
        phases: str | set[str],
        *,
        timeout: float = 5.0,
        poll_interval: float = 0.05,
    ) -> ExternalBalatroObservation:
        expected = {phases} if isinstance(phases, str) else set(phases)
        if not expected:
            raise ValueError("at least one target phase is required")

        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            observation = self.observe()
            if observation.phase.phase in expected:
                return observation
            if time.monotonic() >= deadline:
                names = ", ".join(sorted(expected))
                raise TimeoutError(
                    "Balatro did not reach expected visual phase(s): " + names
                )
            if poll_interval > 0:
                time.sleep(poll_interval)

    def close(self) -> None:
        self.capture.close()

    def __enter__(self) -> ExternalBalatroObserver:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
