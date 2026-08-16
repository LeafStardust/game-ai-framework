from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BalatroDiagnosticEvent:
    session_id: str
    sequence: int
    stage: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "balatro-diagnostic-v1",
            "session_id": self.session_id,
            "sequence": int(self.sequence),
            "stage": self.stage,
            "timestamp": self.timestamp,
            "data": self.data,
        }


def _safe_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _safe_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


class BalatroDiagnosticLogger:
    """Append-only operational failures kept separate from experience JSONL.

    The experience stream records only guarded transitions that actually settled.
    This stream records failures and blocks that must be visible for postmortems
    without making a failed command look like successful gameplay experience.
    """

    SCHEMA = "balatro-diagnostic-v1"

    def __init__(
        self,
        session_id: str,
        *,
        directory: str | Path = "logs/balatro/diagnostics",
    ) -> None:
        normalized = str(session_id).strip()
        if not normalized:
            raise ValueError("diagnostic session_id cannot be empty")
        self.session_id = normalized
        self.directory = Path(directory)
        self.path = self.directory / f"{self.session_id}.jsonl"
        self._sequence = self._existing_sequence()

    @property
    def sequence(self) -> int:
        return self._sequence

    def _existing_sequence(self) -> int:
        if not self.path.exists():
            return 0
        sequence = 0
        for line_number, raw in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"invalid diagnostic JSON at {self.path}:{line_number}"
                ) from error
            if row.get("schema") != self.SCHEMA:
                raise ValueError(
                    f"unexpected diagnostic schema at {self.path}:{line_number}"
                )
            if str(row.get("session_id")) != self.session_id:
                raise ValueError(
                    f"diagnostic session mismatch at {self.path}:{line_number}"
                )
            observed = row.get("sequence")
            expected = sequence + 1
            if observed != expected:
                raise ValueError(
                    "diagnostic sequence is not contiguous: "
                    f"expected {expected}, observed {observed!r}"
                )
            sequence = expected
        return sequence

    def record(self, stage: str, **data: Any) -> BalatroDiagnosticEvent:
        stage_name = str(stage).strip()
        if not stage_name:
            raise ValueError("diagnostic stage cannot be empty")
        self._sequence += 1
        event = BalatroDiagnosticEvent(
            session_id=self.session_id,
            sequence=self._sequence,
            stage=stage_name,
            data=_safe_value(data),
        )
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    event.to_dict(),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )
        return event

    def failure(
        self,
        *,
        stage: str,
        error: BaseException,
        status: dict[str, Any] | None = None,
        action: str | None = None,
        phase: str | None = None,
        checkpoint_sequence: int | None = None,
    ) -> BalatroDiagnosticEvent:
        return self.record(
            stage,
            error_type=type(error).__name__,
            error=str(error),
            status=status or {},
            action=action,
            phase=phase,
            checkpoint_sequence=checkpoint_sequence,
        )
