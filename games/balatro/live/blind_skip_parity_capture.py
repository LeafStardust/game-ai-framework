"""Opt-in private R5 capture stream for exact Economy-Tag blind skips."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from games.balatro.actions import SKIP_BLIND
from games.balatro.env.actions import EnvAction
from games.balatro.env.strategic_evidence import (
    build_public_strategic_transition_evidence,
    skip_blind_with_public_evidence,
)
from games.balatro.env.transition import HeadlessTransitionError
from games.balatro.live.blind_skip_parity_checkpoint import (
    LiveBlindSkipParityCheckpoint,
    LiveBlindSkipProgression,
    LiveBlindSkipReplayComparison,
    capture_live_blind_skip_parity_checkpoint,
    compare_live_blind_skip_replay,
    headless_blind_skip_run_from_live_checkpoint,
)
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_autonomous_step_injected import _same_snapshot
from games.balatro.live.translator import DefaultBalatroStateTranslator


class LiveBlindSkipParityCaptureError(RuntimeError):
    """Raised when a live blind skip cannot produce coherent private evidence."""


def _exact_nonnegative_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LiveBlindSkipParityCaptureError(f"{field} must be a nonnegative integer")
    return value


def blind_skip_parity_checkpoint_to_payload(
    checkpoint: LiveBlindSkipParityCheckpoint,
) -> dict[str, Any]:
    if not isinstance(checkpoint, LiveBlindSkipParityCheckpoint):
        raise TypeError("checkpoint must be LiveBlindSkipParityCheckpoint")
    snapshot = checkpoint.public_snapshot
    return {
        "public_snapshot": {
            "sequence": int(snapshot.sequence),
            "phase": str(snapshot.phase),
            "state_complete": bool(snapshot.state_complete),
            "payload": deepcopy(snapshot.payload),
        },
        "progression": {
            "small_status": checkpoint.progression.small_status,
            "big_status": checkpoint.progression.big_status,
            "boss_status": checkpoint.progression.boss_status,
            "blind_on_deck": checkpoint.progression.blind_on_deck,
            "blind_ante": checkpoint.progression.blind_ante,
            "small_tag": checkpoint.progression.small_tag,
            "big_tag": checkpoint.progression.big_tag,
        },
        "active_tag_count": checkpoint.active_tag_count,
        "skips": checkpoint.skips,
    }


def blind_skip_parity_checkpoint_from_payload(
    payload: dict[str, Any],
) -> LiveBlindSkipParityCheckpoint:
    if not isinstance(payload, dict):
        raise LiveBlindSkipParityCaptureError("blind-skip checkpoint must be a mapping")
    public = payload.get("public_snapshot")
    progression = payload.get("progression")
    if not isinstance(public, dict) or not isinstance(progression, dict):
        raise LiveBlindSkipParityCaptureError(
            "blind-skip checkpoint requires public_snapshot and progression mappings"
        )
    phase = public.get("phase")
    state_complete = public.get("state_complete")
    public_payload = public.get("payload")
    if not isinstance(phase, str) or not phase:
        raise LiveBlindSkipParityCaptureError("public_snapshot.phase must be non-empty")
    if not isinstance(state_complete, bool):
        raise LiveBlindSkipParityCaptureError("public_snapshot.state_complete must be boolean")
    if not isinstance(public_payload, dict):
        raise LiveBlindSkipParityCaptureError("public_snapshot.payload must be a mapping")
    try:
        blind_ante = progression["blind_ante"]
        if isinstance(blind_ante, bool) or not isinstance(blind_ante, int):
            raise TypeError("blind_ante must be an exact integer")
        fields = {
            name: progression[name]
            for name in (
                "small_status",
                "big_status",
                "boss_status",
                "blind_on_deck",
                "small_tag",
                "big_tag",
            )
        }
        if any(not isinstance(value, str) or not value.strip() for value in fields.values()):
            raise TypeError("progression strings must be exact and nonempty")
        private_progression = LiveBlindSkipProgression(
            blind_ante=blind_ante,
            **fields,
        )
        private_progression.to_headless()
    except (KeyError, TypeError, ValueError) as exc:
        raise LiveBlindSkipParityCaptureError(
            "progression payload is not exact canonical blind authority"
        ) from exc
    return LiveBlindSkipParityCheckpoint(
        public_snapshot=LiveBalatroSnapshot(
            sequence=_exact_nonnegative_int(
                public.get("sequence"), field="public_snapshot.sequence"
            ),
            phase=phase,
            state_complete=state_complete,
            payload=deepcopy(public_payload),
        ),
        progression=private_progression,
        active_tag_count=_exact_nonnegative_int(
            payload.get("active_tag_count"), field="active_tag_count"
        ),
        skips=_exact_nonnegative_int(payload.get("skips"), field="skips"),
    )


def compare_captured_live_blind_skip(
    before: LiveBlindSkipParityCheckpoint,
    after: LiveBlindSkipParityCheckpoint,
) -> LiveBlindSkipReplayComparison:
    before_run = headless_blind_skip_run_from_live_checkpoint(before)
    after_public = DefaultBalatroStateTranslator().translate(after.public_snapshot)
    live_evidence = build_public_strategic_transition_evidence(
        before_run.public,
        EnvAction.from_alias("SKIP_BLIND"),
        after_public,
    )
    return compare_live_blind_skip_replay(before, after, live_evidence)


def _require_parameterless_skip_blind(action) -> None:
    if str(getattr(action, "name", "")) != SKIP_BLIND:
        raise LiveBlindSkipParityCaptureError("parity recorder only accepts SKIP_BLIND")
    if tuple(getattr(action, "cards", ()) or ()):
        raise LiveBlindSkipParityCaptureError("SKIP_BLIND parity action must not select cards")
    if getattr(action, "target", None) is not None:
        raise LiveBlindSkipParityCaptureError("SKIP_BLIND parity action must be parameterless")


class LiveBlindSkipParityRecorder:
    """Append exact private replay evidence for supported skips in one live run."""

    SCHEMA = "balatro-r5-blind-skip-parity-v1"

    def __init__(self, run_id: str, observer, *, directory: str | Path) -> None:
        normalized = str(run_id).strip()
        if not normalized:
            raise ValueError("blind-skip parity run_id cannot be empty")
        if normalized in {".", ".."} or "/" in normalized or "\\" in normalized:
            raise ValueError("blind-skip parity run_id cannot contain path separators")
        self.run_id = normalized
        self.observer = observer
        self.directory = Path(directory)
        self.path = self.directory / f"{self.run_id}.blind-skip-parity.jsonl"
        self._sequence = self._existing_sequence()

    @property
    def sequence(self) -> int:
        return self._sequence

    def _existing_sequence(self) -> int:
        if not self.path.exists():
            return 0
        sequence = 0
        for line_number, raw in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise LiveBlindSkipParityCaptureError(
                    f"invalid blind-skip parity JSON at {self.path}:{line_number}"
                ) from exc
            if row.get("schema") != self.SCHEMA or str(row.get("run_id")) != self.run_id:
                raise LiveBlindSkipParityCaptureError(
                    f"unexpected blind-skip parity row at {self.path}:{line_number}"
                )
            expected = sequence + 1
            if row.get("sequence") != expected:
                raise LiveBlindSkipParityCaptureError(
                    f"blind-skip parity sequence expected {expected}, observed {row.get('sequence')!r}"
                )
            sequence = expected
        return sequence

    def capture_before(self, decision) -> LiveBlindSkipParityCheckpoint:
        _require_parameterless_skip_blind(decision.action)
        checkpoint = capture_live_blind_skip_parity_checkpoint(self.observer)
        if not _same_snapshot(decision.snapshot, checkpoint.public_snapshot):
            raise LiveBlindSkipParityCaptureError(
                "planned SKIP_BLIND snapshot does not match private pre-skip checkpoint"
            )
        try:
            run = headless_blind_skip_run_from_live_checkpoint(checkpoint)
            skip_blind_with_public_evidence(run)
        except (HeadlessTransitionError, RuntimeError, TypeError, ValueError) as exc:
            raise LiveBlindSkipParityCaptureError(
                "live checkpoint does not admit the exact Economy-Tag skip subset"
            ) from exc
        return checkpoint

    def record_after(
        self,
        before: LiveBlindSkipParityCheckpoint,
        decision,
        dispatch_result,
    ) -> LiveBlindSkipReplayComparison:
        _require_parameterless_skip_blind(decision.action)
        _require_parameterless_skip_blind(dispatch_result.action)
        if not _same_snapshot(decision.snapshot, dispatch_result.before):
            raise LiveBlindSkipParityCaptureError(
                "settled SKIP_BLIND result does not begin at the planned snapshot"
            )
        after = capture_live_blind_skip_parity_checkpoint(self.observer)
        if not _same_snapshot(dispatch_result.after, after.public_snapshot):
            raise LiveBlindSkipParityCaptureError(
                "settled SKIP_BLIND result does not match private post-skip checkpoint"
            )
        comparison = compare_captured_live_blind_skip(before, after)
        self._sequence += 1
        row = {
            "schema": self.SCHEMA,
            "run_id": self.run_id,
            "sequence": self._sequence,
            "action": SKIP_BLIND,
            "before": blind_skip_parity_checkpoint_to_payload(before),
            "after": blind_skip_parity_checkpoint_to_payload(after),
            "comparison": {
                "matches": bool(comparison.matches),
                "differences": list(comparison.differences),
                "public_matches": bool(comparison.public.matches),
                "public_differences": list(comparison.public.differences),
            },
        }
        self.directory.mkdir(parents=True, exist_ok=True)
        try:
            encoded = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            self._sequence -= 1
            raise LiveBlindSkipParityCaptureError(
                "blind-skip parity checkpoint is not JSON serializable"
            ) from exc
        try:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(encoded + "\n")
        except OSError:
            self._sequence -= 1
            raise
        return comparison
