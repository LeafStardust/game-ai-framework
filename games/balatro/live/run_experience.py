from __future__ import annotations

import json
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
    """

    def __init__(
        self,
        run: BalatroRunIdentity,
        *,
        directory: str | Path = "logs/balatro/runs",
    ):
        self.run = run
        self.directory = Path(directory)
        self.path = self.directory / f"{run.run_id}.jsonl"
        self._sequence = 0

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
        return self.record(
            "run_finished",
            won=bool(won),
            reason=reason,
            state=state,
        )
