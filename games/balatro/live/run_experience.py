from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class BalatroRunIdentity:
    """Stable metadata attached to every event from one live Balatro run."""

    run_id: str
    deck: str
    stake: str
    playbook: str
    playbook_version: str = "0"

    @classmethod
    def create(
        cls,
        *,
        deck: str,
        stake: str,
        playbook: str,
        playbook_version: str = "0",
    ) -> "BalatroRunIdentity":
        return cls(
            run_id=uuid4().hex,
            deck=str(deck).upper(),
            stake=str(stake).upper(),
            playbook=str(playbook),
            playbook_version=str(playbook_version),
        )


@dataclass(frozen=True)
class BalatroRunEvent:
    run: BalatroRunIdentity
    sequence: int
    event: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "balatro-run-experience-v1",
            "run_id": self.run.run_id,
            "deck": self.run.deck,
            "stake": self.run.stake,
            "playbook": self.run.playbook,
            "playbook_version": self.run.playbook_version,
            "sequence": int(self.sequence),
            "event": self.event,
            "timestamp": self.timestamp,
            "data": self.data,
        }


class BalatroRunExperienceLogger:
    """Append-only JSONL experience log for completed and in-progress runs.

    Recording is intentionally separate from learning. The live agent may write
    observations, decisions, execution results, blind/shop outcomes and the final
    run result here, but this class never changes a playbook or policy. Later
    offline analysis can consume the logs without making live behaviour opaque.

    A logger can be reconstructed in a later Python process with the same run
    identity. Existing events are validated before the sequence resumes, which is
    required by the guarded one-action live workflow where each invocation exits
    after exactly one gameplay action.
    """

    EVENT_SCHEMA = "balatro-run-experience-v1"
    SUMMARY_SCHEMA = "balatro-run-summary-v1"

    def __init__(
        self,
        run: BalatroRunIdentity,
        *,
        directory: str | Path = "logs/balatro/runs",
    ):
        self.run = run
        self.directory = Path(directory)
        self.path = self.directory / f"{run.run_id}.jsonl"
        self.summary_path = self.directory / f"{run.run_id}.summary.json"
        self._sequence = self._existing_sequence()

    @property
    def sequence(self) -> int:
        return self._sequence

    def _identity_fields(self) -> dict[str, str]:
        return {
            "run_id": self.run.run_id,
            "deck": self.run.deck,
            "stake": self.run.stake,
            "playbook": self.run.playbook,
            "playbook_version": self.run.playbook_version,
        }

    def _read_rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []

        rows: list[dict[str, Any]] = []
        expected = self._identity_fields()
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
                    f"invalid run log JSON at {self.path}:{line_number}"
                ) from error
            if row.get("schema") != self.EVENT_SCHEMA:
                raise ValueError(
                    f"unexpected run log schema at {self.path}:{line_number}"
                )
            for key, value in expected.items():
                if str(row.get(key)) != str(value):
                    raise ValueError(
                        "run log identity mismatch for "
                        f"{key}: expected {value!r}, observed {row.get(key)!r}"
                    )
            sequence = row.get("sequence")
            if isinstance(sequence, bool) or not isinstance(sequence, int):
                raise ValueError(
                    f"invalid run log sequence at {self.path}:{line_number}"
                )
            rows.append(row)
        return rows

    def _existing_sequence(self) -> int:
        rows = self._read_rows()
        if not rows:
            return 0

        sequences = [int(row["sequence"]) for row in rows]
        expected = list(range(1, len(sequences) + 1))
        if sequences != expected:
            raise ValueError(
                "run log sequence is not contiguous from 1: "
                f"observed {sequences!r}"
            )
        return sequences[-1]

    def record(self, event: str, **data: Any) -> BalatroRunEvent:
        event_name = str(event).strip()
        if not event_name:
            raise ValueError("run event name cannot be empty")

        self._sequence += 1
        item = BalatroRunEvent(
            run=self.run,
            sequence=self._sequence,
            event=event_name,
            data=data,
        )
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    item.to_dict(),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )
        return item

    def run_started(self, *, state: dict[str, Any] | None = None) -> BalatroRunEvent:
        return self.record("run_started", state=state or {})

    def observation(self, state: dict[str, Any]) -> BalatroRunEvent:
        return self.record("observation", state=state)

    def decision(
        self,
        *,
        action: dict[str, Any],
        rationale: dict[str, Any] | None = None,
    ) -> BalatroRunEvent:
        return self.record(
            "decision",
            action=action,
            rationale=rationale or {},
        )

    def action_result(
        self,
        *,
        action: dict[str, Any],
        success: bool,
        state: dict[str, Any],
    ) -> BalatroRunEvent:
        return self.record(
            "action_result",
            action=action,
            success=bool(success),
            state=state,
        )

    def run_finished(
        self,
        *,
        won: bool,
        state: dict[str, Any],
        reason: str | None = None,
    ) -> BalatroRunEvent:
        event = self.record(
            "run_finished",
            won=bool(won),
            reason=reason,
            state=state,
        )
        self.write_summary(won=won, state=state, reason=reason)
        return event

    def write_summary(
        self,
        *,
        won: bool,
        state: dict[str, Any],
        reason: str | None = None,
    ) -> Path:
        rows = self._read_rows()
        event_counts = Counter(str(row["event"]) for row in rows)
        summary = {
            "schema": self.SUMMARY_SCHEMA,
            **self._identity_fields(),
            "won": bool(won),
            "reason": reason,
            "event_count": len(rows),
            "last_sequence": self._sequence,
            "event_counts": dict(sorted(event_counts.items())),
            "final_state": state,
        }
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary_path = self.summary_path.with_suffix(
            self.summary_path.suffix + ".tmp"
        )
        temporary_path.write_text(
            json.dumps(
                summary,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(self.summary_path)
        return self.summary_path
