"""Opt-in private R5 replay capture for exact held-Planet use."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from games.balatro.actions import USE_CONSUMABLE
from games.balatro.env.actions import EnvAction
from games.balatro.env.consumable_centers import (
    VANILLA_PLANET_CENTER_ORDER,
    VANILLA_TAROT_CENTER_ORDER,
)
from games.balatro.env.parity import (
    PublicStrategicParityComparison,
    compare_public_strategic_evidence,
)
from games.balatro.env.strategic_evidence import (
    build_public_strategic_transition_evidence,
    use_planet_with_public_evidence,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.live.parity_capture import _canonical_held_planet_action
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_autonomous_step_injected import _same_snapshot
from games.balatro.live.runtime.luajit_memory import LuaJITMemoryError
from games.balatro.live.runtime.process_memory import BalatroProcessMemoryError
from games.balatro.live.translator import DefaultBalatroStateTranslator


_TOTAL_KEYS = ("tarot", "planet", "spectral", "tarot_planet", "all")
_SPECTRAL_CENTER_KEYS = frozenset(
    {
        "c_familiar",
        "c_grim",
        "c_incantation",
        "c_talisman",
        "c_aura",
        "c_wraith",
        "c_sigil",
        "c_ouija",
        "c_ectoplasm",
        "c_immolate",
        "c_ankh",
        "c_deja_vu",
        "c_hex",
        "c_trance",
        "c_medium",
        "c_cryptid",
        "c_soul",
        "c_black_hole",
    }
)
_EXPECTED_SET_BY_CENTER = {
    **{key: "Tarot" for key in VANILLA_TAROT_CENTER_ORDER},
    **{key: "Planet" for key in VANILLA_PLANET_CENTER_ORDER},
    **{key: "Spectral" for key in _SPECTRAL_CENTER_KEYS},
}


class LiveHeldPlanetParityCaptureError(RuntimeError):
    """Raised when exact held-Planet replay authority is unavailable."""


@dataclass(frozen=True)
class LiveConsumableUsageState:
    counts: dict[str, int]
    sets: dict[str, str]
    totals: dict[str, int]


@dataclass(frozen=True)
class LiveHeldPlanetParityCheckpoint:
    public_snapshot: LiveBalatroSnapshot
    usage: LiveConsumableUsageState


@dataclass(frozen=True)
class LiveHeldPlanetReplayComparison:
    matches: bool
    differences: tuple[str, ...]
    public: PublicStrategicParityComparison


def _table(decoder, value, *, field: str) -> dict[str, Any]:
    if value is None or getattr(value, "kind", None) != "table":
        raise LiveHeldPlanetParityCaptureError(f"{field} table is unavailable")
    try:
        return decoder.string_fields(int(value.value))
    except (BalatroProcessMemoryError, LuaJITMemoryError, TypeError, ValueError) as exc:
        raise LiveHeldPlanetParityCaptureError(f"unable to read {field} table") from exc


def _lua_exact_int(value, *, field: str, minimum: int = 0) -> int:
    if value is None or getattr(value, "kind", None) not in {"integer", "number"}:
        raise LiveHeldPlanetParityCaptureError(f"{field} must be an exact integer")
    raw = value.value
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not float(raw).is_integer():
        raise LiveHeldPlanetParityCaptureError(f"{field} must be an exact integer")
    result = int(raw)
    if result < minimum:
        raise LiveHeldPlanetParityCaptureError(f"{field} is below its exact minimum")
    return result


def _lua_string(value, *, field: str) -> str:
    if value is None or getattr(value, "kind", None) != "string":
        raise LiveHeldPlanetParityCaptureError(f"{field} must be an exact string")
    result = str(value.value)
    if not result:
        raise LiveHeldPlanetParityCaptureError(f"{field} must be an exact string")
    return result


def _private_usage_state(decoder, root) -> LiveConsumableUsageState:
    game = _table(decoder, root.get("GAME"), field="G.GAME")
    raw_usage = game.get("consumeable_usage")
    raw_totals = game.get("consumeable_usage_total")

    # Vanilla leaves both fields nil before the first consumable use. That state is
    # exactly equivalent to the zero table created by set_consumeable_usage.
    if raw_usage is None and raw_totals is None:
        return LiveConsumableUsageState(
            counts={},
            sets={},
            totals={key: 0 for key in _TOTAL_KEYS},
        )
    if raw_usage is None or raw_totals is None:
        raise LiveHeldPlanetParityCaptureError(
            "consumable usage history is only partially available"
        )

    usage = _table(decoder, raw_usage, field="G.GAME.consumeable_usage")
    counts: dict[str, int] = {}
    sets: dict[str, str] = {}
    for key, value in usage.items():
        expected_set = _EXPECTED_SET_BY_CENTER.get(key)
        if expected_set is None:
            raise LiveHeldPlanetParityCaptureError(
                f"G.GAME.consumeable_usage contains unknown center {key!r}"
            )
        record = _table(
            decoder,
            value,
            field=f"G.GAME.consumeable_usage[{key!r}]",
        )
        count = _lua_exact_int(
            record.get("count"),
            field=f"G.GAME.consumeable_usage[{key!r}].count",
            minimum=1,
        )
        card_set = _lua_string(
            record.get("set"),
            field=f"G.GAME.consumeable_usage[{key!r}].set",
        )
        _lua_exact_int(
            record.get("order"),
            field=f"G.GAME.consumeable_usage[{key!r}].order",
            minimum=1,
        )
        if card_set != expected_set:
            raise LiveHeldPlanetParityCaptureError(
                f"G.GAME.consumeable_usage[{key!r}].set is inconsistent"
            )
        counts[key] = count
        sets[key] = card_set

    totals_table = _table(
        decoder,
        raw_totals,
        field="G.GAME.consumeable_usage_total",
    )
    if set(totals_table) != set(_TOTAL_KEYS):
        raise LiveHeldPlanetParityCaptureError(
            "G.GAME.consumeable_usage_total is incomplete or contains unknown fields"
        )
    totals = {
        key: _lua_exact_int(
            totals_table.get(key),
            field=f"G.GAME.consumeable_usage_total.{key}",
        )
        for key in _TOTAL_KEYS
    }
    expected_tarot = sum(
        count for key, count in counts.items() if sets[key] == "Tarot"
    )
    expected_planet = sum(
        count for key, count in counts.items() if sets[key] == "Planet"
    )
    expected_spectral = sum(
        count for key, count in counts.items() if sets[key] == "Spectral"
    )
    expected_totals = {
        "tarot": expected_tarot,
        "planet": expected_planet,
        "spectral": expected_spectral,
        "tarot_planet": expected_tarot + expected_planet,
        "all": expected_tarot + expected_planet + expected_spectral,
    }
    if totals != expected_totals:
        raise LiveHeldPlanetParityCaptureError(
            "G.GAME consumable usage counts and totals are inconsistent"
        )
    return LiveConsumableUsageState(counts=counts, sets=sets, totals=totals)


def _capture_stable_live_usage(observer) -> tuple[LiveBalatroSnapshot, LiveConsumableUsageState]:
    before = observer.observe()
    if not isinstance(before, LiveBalatroSnapshot):
        raise LiveHeldPlanetParityCaptureError(
            "observer did not return LiveBalatroSnapshot"
        )
    if before.phase != "SHOP" or before.state_complete is not True:
        raise LiveHeldPlanetParityCaptureError(
            "held-Planet parity checkpoint requires complete SHOP"
        )
    try:
        decoder, _, root = observer._root()
        first_usage = _private_usage_state(decoder, root)
        after = observer.observe()
        decoder, _, root = observer._root()
        second_usage = _private_usage_state(decoder, root)
    except (OSError, RuntimeError) as exc:
        if isinstance(exc, LiveHeldPlanetParityCaptureError):
            raise
        raise LiveHeldPlanetParityCaptureError(
            "unable to capture exact live held-Planet replay authority"
        ) from exc
    if before != after or first_usage != second_usage:
        raise LiveHeldPlanetParityCaptureError(
            "live held-Planet state changed while capturing replay authority"
        )
    return deepcopy(before), deepcopy(first_usage)


def capture_live_held_planet_parity_checkpoint(
    observer,
) -> LiveHeldPlanetParityCheckpoint:
    snapshot, usage = _capture_stable_live_usage(observer)
    checkpoint = LiveHeldPlanetParityCheckpoint(snapshot, usage)
    headless_held_planet_run_from_checkpoint(checkpoint)
    return checkpoint


def headless_held_planet_run_from_checkpoint(
    checkpoint: LiveHeldPlanetParityCheckpoint,
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> HeadlessRunState:
    if not isinstance(checkpoint, LiveHeldPlanetParityCheckpoint):
        raise TypeError("checkpoint must be LiveHeldPlanetParityCheckpoint")
    if checkpoint.public_snapshot.phase != "SHOP" or checkpoint.public_snapshot.state_complete is not True:
        raise LiveHeldPlanetParityCaptureError(
            "headless held-Planet restoration requires complete SHOP"
        )
    usage = checkpoint.usage
    if not isinstance(usage, LiveConsumableUsageState):
        raise LiveHeldPlanetParityCaptureError("held-Planet usage authority is malformed")
    if set(usage.totals) != set(_TOTAL_KEYS):
        raise LiveHeldPlanetParityCaptureError("held-Planet usage totals are incomplete")
    translator = translator or DefaultBalatroStateTranslator()
    public = translator.translate(checkpoint.public_snapshot)
    try:
        return HeadlessRunState(
            public=public,
            seed="R5-HELD-PLANET-REPLAY",
            consumable_usage_observed=True,
            consumable_usage_counts=deepcopy(usage.counts),
            consumable_usage_totals=deepcopy(usage.totals),
        )
    except (TypeError, ValueError, HeadlessTransitionError) as exc:
        raise LiveHeldPlanetParityCaptureError(
            "held-Planet checkpoint cannot restore exact headless authority"
        ) from exc


def _action_for_checkpoint(checkpoint: LiveHeldPlanetParityCheckpoint, action) -> EnvAction:
    if tuple(getattr(action, "cards", ()) or ()):
        raise LiveHeldPlanetParityCaptureError(
            "held Planet USE_CONSUMABLE must not target hand cards"
        )
    target = getattr(action, "target", None)
    read = target.get if isinstance(target, dict) else lambda key, default=None: getattr(target, key, default)
    value = {
        "name": str(getattr(action, "name", "")),
        "target": {
            "area_index": read("area_index"),
            "name": read("name", read("label")),
        },
    }
    try:
        canonical = _canonical_held_planet_action(
            value,
            headless_held_planet_run_from_checkpoint(checkpoint).public,
        )
    except ValueError as exc:
        raise LiveHeldPlanetParityCaptureError(str(exc)) from exc
    if canonical is None:
        raise LiveHeldPlanetParityCaptureError(
            "held-Planet parity accepts only USE_CONSUMABLE"
        )
    return canonical


def compare_captured_live_held_planet(
    before: LiveHeldPlanetParityCheckpoint,
    action,
    after_snapshot: LiveBalatroSnapshot,
    after_usage: LiveConsumableUsageState,
) -> LiveHeldPlanetReplayComparison:
    run = headless_held_planet_run_from_checkpoint(before)
    canonical_action = _action_for_checkpoint(before, action)
    if after_snapshot.phase != "SHOP" or after_snapshot.state_complete is not True:
        raise LiveHeldPlanetParityCaptureError(
            "held-Planet action did not settle at complete SHOP"
        )
    live_after = DefaultBalatroStateTranslator().translate(after_snapshot)
    live_evidence = build_public_strategic_transition_evidence(
        run.public,
        canonical_action,
        live_after,
    )
    try:
        result, simulator_evidence = use_planet_with_public_evidence(
            run,
            consumable_index=canonical_action.payload()["consumable_index"],
        )
    except HeadlessTransitionError as exc:
        raise LiveHeldPlanetParityCaptureError(
            f"held-Planet checkpoint does not admit exact replay: {exc}"
        ) from exc
    public = compare_public_strategic_evidence(live_evidence, simulator_evidence)
    differences = [f"public.{item}" for item in public.differences]
    if after_usage.counts != result.consumable_usage_counts:
        differences.append("private.usage_counts")
    if after_usage.sets != before.usage.sets:
        differences.append("private.usage_sets")
    if after_usage.totals != result.consumable_usage_totals:
        differences.append("private.usage_totals")
    return LiveHeldPlanetReplayComparison(
        matches=not differences,
        differences=tuple(differences),
        public=public,
    )


def _exact_nonnegative_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LiveHeldPlanetParityCaptureError(f"{field} must be a nonnegative integer")
    return value


def _snapshot_to_payload(snapshot: LiveBalatroSnapshot) -> dict[str, Any]:
    return {
        "sequence": int(snapshot.sequence),
        "phase": str(snapshot.phase),
        "state_complete": bool(snapshot.state_complete),
        "payload": deepcopy(snapshot.payload),
    }


def _snapshot_from_payload(payload: dict[str, Any]) -> LiveBalatroSnapshot:
    if not isinstance(payload, dict) or not isinstance(payload.get("payload"), dict):
        raise LiveHeldPlanetParityCaptureError("public snapshot payload is malformed")
    phase = payload.get("phase")
    complete = payload.get("state_complete")
    if not isinstance(phase, str) or not phase or not isinstance(complete, bool):
        raise LiveHeldPlanetParityCaptureError("public snapshot metadata is malformed")
    return LiveBalatroSnapshot(
        sequence=_exact_nonnegative_int(payload.get("sequence"), field="sequence"),
        phase=phase,
        state_complete=complete,
        payload=deepcopy(payload["payload"]),
    )


def _usage_to_payload(usage: LiveConsumableUsageState) -> dict[str, Any]:
    return {
        "counts": deepcopy(usage.counts),
        "sets": deepcopy(usage.sets),
        "totals": deepcopy(usage.totals),
    }


def _usage_from_payload(payload: dict[str, Any]) -> LiveConsumableUsageState:
    if not isinstance(payload, dict):
        raise LiveHeldPlanetParityCaptureError("consumable usage payload is malformed")
    counts = payload.get("counts")
    sets = payload.get("sets")
    totals = payload.get("totals")
    if not isinstance(counts, dict) or not isinstance(sets, dict) or not isinstance(totals, dict):
        raise LiveHeldPlanetParityCaptureError("consumable usage payload is malformed")
    if set(counts) != set(sets):
        raise LiveHeldPlanetParityCaptureError("consumable usage identities are incomplete")
    for key, count in counts.items():
        if key not in _EXPECTED_SET_BY_CENTER or _exact_nonnegative_int(count, field=key) < 1:
            raise LiveHeldPlanetParityCaptureError("consumable usage identity is invalid")
        if sets[key] != _EXPECTED_SET_BY_CENTER[key]:
            raise LiveHeldPlanetParityCaptureError("consumable usage set is inconsistent")
    if set(totals) != set(_TOTAL_KEYS):
        raise LiveHeldPlanetParityCaptureError("consumable usage totals are incomplete")
    normalized_totals = {
        key: _exact_nonnegative_int(totals[key], field=key) for key in _TOTAL_KEYS
    }
    usage = LiveConsumableUsageState(
        counts={str(key): int(value) for key, value in counts.items()},
        sets={str(key): str(value) for key, value in sets.items()},
        totals=normalized_totals,
    )
    expected = {
        "tarot": sum(v for k, v in usage.counts.items() if usage.sets[k] == "Tarot"),
        "planet": sum(v for k, v in usage.counts.items() if usage.sets[k] == "Planet"),
        "spectral": sum(v for k, v in usage.counts.items() if usage.sets[k] == "Spectral"),
    }
    expected["tarot_planet"] = expected["tarot"] + expected["planet"]
    expected["all"] = expected["tarot_planet"] + expected["spectral"]
    if usage.totals != expected:
        raise LiveHeldPlanetParityCaptureError("consumable usage counts and totals are inconsistent")
    return usage


def held_planet_parity_checkpoint_to_payload(
    checkpoint: LiveHeldPlanetParityCheckpoint,
) -> dict[str, Any]:
    return {
        "public_snapshot": _snapshot_to_payload(checkpoint.public_snapshot),
        "usage": _usage_to_payload(checkpoint.usage),
    }


def held_planet_parity_checkpoint_from_payload(
    payload: dict[str, Any],
) -> LiveHeldPlanetParityCheckpoint:
    if not isinstance(payload, dict):
        raise LiveHeldPlanetParityCaptureError("held-Planet checkpoint must be a mapping")
    checkpoint = LiveHeldPlanetParityCheckpoint(
        public_snapshot=_snapshot_from_payload(payload.get("public_snapshot")),
        usage=_usage_from_payload(payload.get("usage")),
    )
    headless_held_planet_run_from_checkpoint(checkpoint)
    return checkpoint


class LiveHeldPlanetParityRecorder:
    SCHEMA = "balatro-r5-held-planet-parity-v1"

    def __init__(self, run_id: str, observer, *, directory: str | Path) -> None:
        normalized = str(run_id).strip()
        if not normalized or normalized in {".", ".."} or "/" in normalized or "\\" in normalized:
            raise ValueError("held-Planet parity run_id is invalid")
        self.run_id = normalized
        self.observer = observer
        self.directory = Path(directory)
        self.path = self.directory / f"{self.run_id}.held-planet-parity.jsonl"
        self._sequence = self._existing_sequence()

    def _existing_sequence(self) -> int:
        if not self.path.exists():
            return 0
        sequence = 0
        for line_number, raw in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            if not raw.strip():
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise LiveHeldPlanetParityCaptureError(
                    f"invalid held-Planet parity JSON at {self.path}:{line_number}"
                ) from exc
            expected = sequence + 1
            if row.get("schema") != self.SCHEMA or str(row.get("run_id")) != self.run_id or row.get("sequence") != expected:
                raise LiveHeldPlanetParityCaptureError(
                    f"unexpected held-Planet parity row at {self.path}:{line_number}"
                )
            sequence = expected
        return sequence

    def capture_before(self, decision) -> LiveHeldPlanetParityCheckpoint:
        checkpoint = capture_live_held_planet_parity_checkpoint(self.observer)
        if not _same_snapshot(decision.snapshot, checkpoint.public_snapshot):
            raise LiveHeldPlanetParityCaptureError(
                "planned held-Planet snapshot does not match private checkpoint"
            )
        _action_for_checkpoint(checkpoint, decision.action)
        return checkpoint

    def record_after(self, before, decision, dispatch_result) -> LiveHeldPlanetReplayComparison:
        if not _same_snapshot(decision.snapshot, dispatch_result.before):
            raise LiveHeldPlanetParityCaptureError(
                "settled held-Planet result does not begin at the planned snapshot"
            )
        planned_action = _action_for_checkpoint(before, decision.action)
        settled_action = _action_for_checkpoint(before, dispatch_result.action)
        if settled_action != planned_action:
            raise LiveHeldPlanetParityCaptureError(
                "settled held-Planet action does not match the planned action"
            )
        observed_after, after_usage = _capture_stable_live_usage(self.observer)
        if not _same_snapshot(dispatch_result.after, observed_after):
            raise LiveHeldPlanetParityCaptureError(
                "settled held-Planet result does not match current public state"
            )
        comparison = compare_captured_live_held_planet(
            before,
            decision.action,
            observed_after,
            after_usage,
        )
        self._sequence += 1
        row = {
            "schema": self.SCHEMA,
            "run_id": self.run_id,
            "sequence": self._sequence,
            "action": {"name": planned_action.action_id, **planned_action.payload()},
            "before": held_planet_parity_checkpoint_to_payload(before),
            "after_public_snapshot": _snapshot_to_payload(observed_after),
            "after_usage": _usage_to_payload(after_usage),
            "comparison": {
                "matches": comparison.matches,
                "differences": list(comparison.differences),
            },
        }
        self.directory.mkdir(parents=True, exist_ok=True)
        try:
            encoded = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(encoded + "\n")
        except (OSError, TypeError, ValueError):
            self._sequence -= 1
            raise
        return comparison
