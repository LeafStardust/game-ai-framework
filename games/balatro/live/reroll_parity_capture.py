"""Private R5 capture stream for exact live paid-reroll parity replay.

This module deliberately keeps RNG replay authority out of policy-visible run
experience.  It is opt-in diagnostic evidence used only to validate the live
REFRESH_SHOP boundary against the headless simulator.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from games.balatro.actions import REFRESH_SHOP
from games.balatro.env.actions import EnvAction
from games.balatro.env.strategic_evidence import build_public_strategic_transition_evidence
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.reroll_parity_checkpoint import (
    LiveRerollParityCheckpoint,
    LiveRerollReplayComparison,
    capture_live_reroll_parity_checkpoint,
    compare_live_reroll_replay,
    headless_reroll_run_from_live_checkpoint,
)
from games.balatro.live.runtime.live_memory_autonomous_step_injected import _same_snapshot
from games.balatro.live.runtime.live_memory_shop_terms import LiveShopRerollTerms


class LiveRerollParityCaptureError(RuntimeError):
    """Raised when one live reroll cannot produce coherent private R5 evidence."""


def _exact_nonnegative_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LiveRerollParityCaptureError(f"{field} must be a nonnegative integer")
    return value


def reroll_parity_checkpoint_to_payload(
    checkpoint: LiveRerollParityCheckpoint,
) -> dict[str, Any]:
    if not isinstance(checkpoint, LiveRerollParityCheckpoint):
        raise TypeError("checkpoint must be LiveRerollParityCheckpoint")
    snapshot = checkpoint.public_snapshot
    return {
        "public_snapshot": {
            "sequence": int(snapshot.sequence),
            "phase": str(snapshot.phase),
            "state_complete": bool(snapshot.state_complete),
            "payload": deepcopy(snapshot.payload),
        },
        "rng_snapshot": deepcopy(checkpoint.rng_snapshot),
        "reroll_terms": {
            "cost": int(checkpoint.reroll_terms.cost),
            "free_rerolls": int(checkpoint.reroll_terms.free_rerolls),
        },
        "active_tag_count": int(checkpoint.active_tag_count),
    }


def reroll_parity_checkpoint_from_payload(payload: dict[str, Any]) -> LiveRerollParityCheckpoint:
    if not isinstance(payload, dict):
        raise LiveRerollParityCaptureError("reroll parity checkpoint payload must be a mapping")
    public = payload.get("public_snapshot")
    rng_snapshot = payload.get("rng_snapshot")
    terms = payload.get("reroll_terms")
    if not isinstance(public, dict):
        raise LiveRerollParityCaptureError("public_snapshot must be a mapping")
    if not isinstance(rng_snapshot, dict):
        raise LiveRerollParityCaptureError("rng_snapshot must be a mapping")
    if not isinstance(terms, dict):
        raise LiveRerollParityCaptureError("reroll_terms must be a mapping")

    sequence = _exact_nonnegative_int(public.get("sequence"), field="public_snapshot.sequence")
    phase = public.get("phase")
    state_complete = public.get("state_complete")
    public_payload = public.get("payload")
    if not isinstance(phase, str) or not phase:
        raise LiveRerollParityCaptureError("public_snapshot.phase must be non-empty")
    if not isinstance(state_complete, bool):
        raise LiveRerollParityCaptureError("public_snapshot.state_complete must be boolean")
    if not isinstance(public_payload, dict):
        raise LiveRerollParityCaptureError("public_snapshot.payload must be a mapping")

    return LiveRerollParityCheckpoint(
        public_snapshot=LiveBalatroSnapshot(
            sequence=sequence,
            phase=phase,
            state_complete=state_complete,
            payload=deepcopy(public_payload),
        ),
        rng_snapshot=deepcopy(rng_snapshot),
        reroll_terms=LiveShopRerollTerms(
            cost=_exact_nonnegative_int(terms.get("cost"), field="reroll_terms.cost"),
            free_rerolls=_exact_nonnegative_int(
                terms.get("free_rerolls"),
                field="reroll_terms.free_rerolls",
            ),
        ),
        active_tag_count=_exact_nonnegative_int(
            payload.get("active_tag_count"),
            field="active_tag_count",
        ),
    )


def compare_captured_live_reroll(
    before: LiveRerollParityCheckpoint,
    after: LiveRerollParityCheckpoint,
) -> LiveRerollReplayComparison:
    """Build exact public evidence from two checkpoints and replay the reroll."""
    canonical_action = EnvAction.from_alias("REROLL_SHOP")
    before_run = headless_reroll_run_from_live_checkpoint(before)
    after_run = headless_reroll_run_from_live_checkpoint(after)
    live_evidence = build_public_strategic_transition_evidence(
        before_run.public,
        canonical_action,
        after_run.public,
    )
    return compare_live_reroll_replay(before, after, live_evidence)


def _require_parameterless_refresh(action) -> None:
    if str(getattr(action, "name", "")) != REFRESH_SHOP:
        raise LiveRerollParityCaptureError("parity recorder only accepts REFRESH_SHOP")
    if tuple(getattr(action, "cards", ()) or ()):
        raise LiveRerollParityCaptureError("REFRESH_SHOP parity action must not select cards")
    if getattr(action, "target", None) is not None:
        raise LiveRerollParityCaptureError("REFRESH_SHOP parity action must be parameterless")


class LiveRerollParityRecorder:
    """Append exact private replay evidence for one live supervisor run."""

    SCHEMA = "balatro-r5-reroll-parity-v1"

    def __init__(
        self,
        run_id: str,
        observer,
        *,
        directory: str | Path,
    ) -> None:
        normalized = str(run_id).strip()
        if not normalized:
            raise ValueError("reroll parity run_id cannot be empty")
        if normalized in {".", ".."} or "/" in normalized or "\\" in normalized:
            raise ValueError("reroll parity run_id cannot contain path separators")
        self.run_id = normalized
        self.observer = observer
        self.directory = Path(directory)
        self.path = self.directory / f"{self.run_id}.reroll-parity.jsonl"
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
                raise LiveRerollParityCaptureError(
                    f"invalid reroll parity JSON at {self.path}:{line_number}"
                ) from error
            if row.get("schema") != self.SCHEMA:
                raise LiveRerollParityCaptureError(
                    f"unexpected reroll parity schema at {self.path}:{line_number}"
                )
            if str(row.get("run_id")) != self.run_id:
                raise LiveRerollParityCaptureError(
                    f"reroll parity run mismatch at {self.path}:{line_number}"
                )
            expected = sequence + 1
            if row.get("sequence") != expected:
                raise LiveRerollParityCaptureError(
                    "reroll parity sequence is not contiguous: "
                    f"expected {expected}, observed {row.get('sequence')!r}"
                )
            sequence = expected
        return sequence

    def capture_before(self, decision) -> LiveRerollParityCheckpoint:
        _require_parameterless_refresh(decision.action)
        checkpoint = capture_live_reroll_parity_checkpoint(self.observer)
        if not _same_snapshot(decision.snapshot, checkpoint.public_snapshot):
            raise LiveRerollParityCaptureError(
                "planned REFRESH_SHOP snapshot does not match private pre-reroll checkpoint"
            )
        return checkpoint

    def record_after(
        self,
        before: LiveRerollParityCheckpoint,
        decision,
        dispatch_result,
    ) -> LiveRerollReplayComparison:
        _require_parameterless_refresh(decision.action)
        _require_parameterless_refresh(dispatch_result.action)
        if not _same_snapshot(decision.snapshot, dispatch_result.before):
            raise LiveRerollParityCaptureError(
                "settled REFRESH_SHOP result does not begin at the planned snapshot"
            )

        after = capture_live_reroll_parity_checkpoint(self.observer)
        if not _same_snapshot(dispatch_result.after, after.public_snapshot):
            raise LiveRerollParityCaptureError(
                "settled REFRESH_SHOP result does not match private post-reroll checkpoint"
            )

        comparison = compare_captured_live_reroll(before, after)
        self._sequence += 1
        row = {
            "schema": self.SCHEMA,
            "run_id": self.run_id,
            "sequence": self._sequence,
            "action": REFRESH_SHOP,
            "before": reroll_parity_checkpoint_to_payload(before),
            "after": reroll_parity_checkpoint_to_payload(after),
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
        except (TypeError, ValueError) as error:
            self._sequence -= 1
            raise LiveRerollParityCaptureError(
                "reroll parity checkpoint is not JSON serializable"
            ) from error
        try:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(encoded + "\n")
        except OSError:
            self._sequence -= 1
            raise
        return comparison
