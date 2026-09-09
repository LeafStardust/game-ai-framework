"""Opt-in private R5 capture stream for exact live blind-start replay."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from games.balatro.actions import SELECT_BLIND
from games.balatro.env.actions import EnvAction
from games.balatro.env.strategic_evidence import build_public_strategic_transition_evidence
from games.balatro.live.blind_start_parity_checkpoint import (
    LiveBlindStartParityCheckpoint,
    LiveBlindStartReplayComparison,
    capture_live_blind_start_parity_checkpoint,
    compare_live_blind_start_replay,
    headless_blind_start_run_from_live_checkpoint,
)
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_autonomous_step_injected import _same_snapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator


class LiveBlindStartParityCaptureError(RuntimeError):
    """Raised when a live blind start cannot produce coherent private evidence."""


def _exact_nonnegative_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LiveBlindStartParityCaptureError(
            f"{field} must be a nonnegative integer"
        )
    return value


def blind_start_parity_checkpoint_to_payload(
    checkpoint: LiveBlindStartParityCheckpoint,
) -> dict[str, Any]:
    if not isinstance(checkpoint, LiveBlindStartParityCheckpoint):
        raise TypeError("checkpoint must be LiveBlindStartParityCheckpoint")
    snapshot = checkpoint.public_snapshot
    return {
        "public_snapshot": {
            "sequence": int(snapshot.sequence),
            "phase": str(snapshot.phase),
            "state_complete": bool(snapshot.state_complete),
            "payload": deepcopy(snapshot.payload),
        },
        "rng_snapshot": deepcopy(checkpoint.rng_snapshot),
        "active_tag_count": int(checkpoint.active_tag_count),
    }


def blind_start_parity_checkpoint_from_payload(
    payload: dict[str, Any],
) -> LiveBlindStartParityCheckpoint:
    if not isinstance(payload, dict):
        raise LiveBlindStartParityCaptureError(
            "blind-start parity checkpoint payload must be a mapping"
        )
    public = payload.get("public_snapshot")
    rng_snapshot = payload.get("rng_snapshot")
    if not isinstance(public, dict):
        raise LiveBlindStartParityCaptureError("public_snapshot must be a mapping")
    if not isinstance(rng_snapshot, dict):
        raise LiveBlindStartParityCaptureError("rng_snapshot must be a mapping")
    phase = public.get("phase")
    state_complete = public.get("state_complete")
    public_payload = public.get("payload")
    if not isinstance(phase, str) or not phase:
        raise LiveBlindStartParityCaptureError(
            "public_snapshot.phase must be non-empty"
        )
    if not isinstance(state_complete, bool):
        raise LiveBlindStartParityCaptureError(
            "public_snapshot.state_complete must be boolean"
        )
    if not isinstance(public_payload, dict):
        raise LiveBlindStartParityCaptureError(
            "public_snapshot.payload must be a mapping"
        )
    return LiveBlindStartParityCheckpoint(
        public_snapshot=LiveBalatroSnapshot(
            sequence=_exact_nonnegative_int(
                public.get("sequence"),
                field="public_snapshot.sequence",
            ),
            phase=phase,
            state_complete=state_complete,
            payload=deepcopy(public_payload),
        ),
        rng_snapshot=deepcopy(rng_snapshot),
        active_tag_count=_exact_nonnegative_int(
            payload.get("active_tag_count"),
            field="active_tag_count",
        ),
    )


def compare_captured_live_blind_start(
    before: LiveBlindStartParityCheckpoint,
    after: LiveBlindStartParityCheckpoint,
) -> LiveBlindStartReplayComparison:
    before_run = headless_blind_start_run_from_live_checkpoint(before)
    after_public = DefaultBalatroStateTranslator().translate(after.public_snapshot)
    live_evidence = build_public_strategic_transition_evidence(
        before_run.public,
        EnvAction.from_alias("SELECT_BLIND"),
        after_public,
    )
    return compare_live_blind_start_replay(before, after, live_evidence)


def _require_parameterless_select_blind(action) -> None:
    if str(getattr(action, "name", "")) != SELECT_BLIND:
        raise LiveBlindStartParityCaptureError(
            "parity recorder only accepts SELECT_BLIND"
        )
    if tuple(getattr(action, "cards", ()) or ()):
        raise LiveBlindStartParityCaptureError(
            "SELECT_BLIND parity action must not select cards"
        )
    if getattr(action, "target", None) is not None:
        raise LiveBlindStartParityCaptureError(
            "SELECT_BLIND parity action must be parameterless"
        )


class LiveBlindStartParityRecorder:
    """Append exact private replay evidence for blind starts in one live run."""

    SCHEMA = "balatro-r5-blind-start-parity-v1"

    def __init__(self, run_id: str, observer, *, directory: str | Path) -> None:
        normalized = str(run_id).strip()
        if not normalized:
            raise ValueError("blind-start parity run_id cannot be empty")
        if normalized in {".", ".."} or "/" in normalized or "\\" in normalized:
            raise ValueError(
                "blind-start parity run_id cannot contain path separators"
            )
        self.run_id = normalized
        self.observer = observer
        self.directory = Path(directory)
        self.path = self.directory / f"{self.run_id}.blind-start-parity.jsonl"
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
            except json.JSONDecodeError as exc:
                raise LiveBlindStartParityCaptureError(
                    f"invalid blind-start parity JSON at {self.path}:{line_number}"
                ) from exc
            if row.get("schema") != self.SCHEMA:
                raise LiveBlindStartParityCaptureError(
                    f"unexpected blind-start parity schema at {self.path}:{line_number}"
                )
            if str(row.get("run_id")) != self.run_id:
                raise LiveBlindStartParityCaptureError(
                    f"blind-start parity run mismatch at {self.path}:{line_number}"
                )
            expected = sequence + 1
            if row.get("sequence") != expected:
                raise LiveBlindStartParityCaptureError(
                    "blind-start parity sequence is not contiguous: "
                    f"expected {expected}, observed {row.get('sequence')!r}"
                )
            sequence = expected
        return sequence

    def capture_before(self, decision) -> LiveBlindStartParityCheckpoint:
        _require_parameterless_select_blind(decision.action)
        checkpoint = capture_live_blind_start_parity_checkpoint(
            self.observer,
            expected_phase="BLIND_SELECT",
        )
        if not _same_snapshot(decision.snapshot, checkpoint.public_snapshot):
            raise LiveBlindStartParityCaptureError(
                "planned SELECT_BLIND snapshot does not match private pre-start checkpoint"
            )
        return checkpoint

    def record_after(
        self,
        before: LiveBlindStartParityCheckpoint,
        decision,
        dispatch_result,
    ) -> LiveBlindStartReplayComparison:
        _require_parameterless_select_blind(decision.action)
        _require_parameterless_select_blind(dispatch_result.action)
        if not _same_snapshot(decision.snapshot, dispatch_result.before):
            raise LiveBlindStartParityCaptureError(
                "settled SELECT_BLIND result does not begin at the planned snapshot"
            )
        after = capture_live_blind_start_parity_checkpoint(
            self.observer,
            expected_phase="SELECTING_HAND",
        )
        if not _same_snapshot(dispatch_result.after, after.public_snapshot):
            raise LiveBlindStartParityCaptureError(
                "settled SELECT_BLIND result does not match private post-start checkpoint"
            )
        comparison = compare_captured_live_blind_start(before, after)
        self._sequence += 1
        row = {
            "schema": self.SCHEMA,
            "run_id": self.run_id,
            "sequence": self._sequence,
            "action": SELECT_BLIND,
            "before": blind_start_parity_checkpoint_to_payload(before),
            "after": blind_start_parity_checkpoint_to_payload(after),
            "comparison": {
                "matches": bool(comparison.matches),
                "differences": list(comparison.differences),
                "public_matches": bool(comparison.public.matches),
                "public_differences": list(comparison.public.differences),
            },
        }
        self.directory.mkdir(parents=True, exist_ok=True)
        try:
            encoded = json.dumps(
                row,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except (TypeError, ValueError) as exc:
            self._sequence -= 1
            raise LiveBlindStartParityCaptureError(
                "blind-start parity checkpoint is not JSON serializable"
            ) from exc
        try:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(encoded + "\n")
        except OSError:
            self._sequence -= 1
            raise
        return comparison
