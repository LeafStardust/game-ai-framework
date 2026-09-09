"""Opt-in private R5 replay capture for exact final Buffoon pack actions."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from games.balatro.actions import SELECT_PACK_CARD, SKIP_BOOSTER
from games.balatro.env.actions import EnvAction
from games.balatro.env.pack import can_choose_pack_option_exact
from games.balatro.env.parity import (
    PublicStrategicParityComparison,
    compare_public_strategic_evidence,
)
from games.balatro.env.strategic_evidence import (
    build_public_strategic_transition_evidence,
    choose_pack_option_with_public_evidence,
    skip_pack_with_public_evidence,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_autonomous_step_injected import _same_snapshot
from games.balatro.live.runtime.live_memory_observer import (
    _normalize_item,
    _phase_name,
    _strict_array_table_values,
)
from games.balatro.live.runtime.luajit_memory import LuaJITMemoryError
from games.balatro.live.runtime.process_memory import BalatroProcessMemoryError
from games.balatro.live.translator import DefaultBalatroStateTranslator


class LiveBuffoonPackParityCaptureError(RuntimeError):
    """Raised when exact final Buffoon replay authority is unavailable."""


@dataclass(frozen=True)
class LiveBuffoonPackParityCheckpoint:
    public_snapshot: LiveBalatroSnapshot
    choices_remaining: int
    return_phase: str
    choices: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class LiveBuffoonPackReplayComparison:
    matches: bool
    differences: tuple[str, ...]
    public: PublicStrategicParityComparison


def _table(decoder, value, *, field: str) -> dict[str, Any]:
    if value is None or getattr(value, "kind", None) != "table":
        raise LiveBuffoonPackParityCaptureError(f"{field} table is unavailable")
    try:
        return decoder.string_fields(int(value.value))
    except (BalatroProcessMemoryError, LuaJITMemoryError, TypeError, ValueError) as exc:
        raise LiveBuffoonPackParityCaptureError(f"unable to read {field} table") from exc


def _exact_nonnegative_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LiveBuffoonPackParityCaptureError(
            f"{field} must be a nonnegative integer"
        )
    return value


def _lua_exact_int(value, *, field: str, minimum: int = 0) -> int:
    if value is None or getattr(value, "kind", None) not in {"integer", "number"}:
        raise LiveBuffoonPackParityCaptureError(f"{field} must be an exact integer")
    raw = value.value
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not float(raw).is_integer():
        raise LiveBuffoonPackParityCaptureError(f"{field} must be an exact integer")
    result = int(raw)
    if result < minimum:
        raise LiveBuffoonPackParityCaptureError(f"{field} is below its exact minimum")
    return result


def _exact_choice_record(data: dict[str, Any], *, area_index: int) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise LiveBuffoonPackParityCaptureError("Buffoon choice must be a mapping")
    result = deepcopy(data)
    result.pop("ui", None)
    if str(result.get("ability_set") or "").upper() != "JOKER":
        raise LiveBuffoonPackParityCaptureError("Buffoon choice must be a visible Joker")
    center = result.get("center")
    label = result.get("label") or result.get("ability_name")
    if not isinstance(center, str) or not center.startswith("j_"):
        raise LiveBuffoonPackParityCaptureError("Buffoon choice center is unavailable")
    if not isinstance(label, str) or not label.strip():
        raise LiveBuffoonPackParityCaptureError("Buffoon choice label is unavailable")
    raw_live_id = result.get("live_id")
    if (
        isinstance(raw_live_id, bool)
        or not isinstance(raw_live_id, (int, float))
        or not float(raw_live_id).is_integer()
        or int(raw_live_id) < 0
    ):
        raise LiveBuffoonPackParityCaptureError("Buffoon choice live_id is unavailable")
    result["live_id"] = int(raw_live_id)
    result["area_index"] = area_index
    if result.get("edition") is not None:
        raise LiveBuffoonPackParityCaptureError("Buffoon choice editions remain unsupported")
    if LiveJokerFactory().create(result) is None:
        raise LiveBuffoonPackParityCaptureError("Buffoon choice Joker is not modeled")
    return result


def _private_pack_terms(decoder, root) -> tuple[int, str, tuple[dict[str, Any], ...]]:
    game = _table(decoder, root.get("GAME"), field="G.GAME")
    choices_remaining = _lua_exact_int(
        game.get("pack_choices"),
        field="G.GAME.pack_choices",
        minimum=1,
    )
    if choices_remaining != 1:
        raise LiveBuffoonPackParityCaptureError(
            "Buffoon parity requires an exact final one-pick pack"
        )
    interrupt = game.get("PACK_INTERRUPT")
    return_phase = _phase_name(decoder, {**root, "STATE": interrupt})
    if return_phase not in {"SHOP", "BLIND_SELECT"}:
        raise LiveBuffoonPackParityCaptureError(
            "Buffoon PACK_INTERRUPT must resolve to SHOP or BLIND_SELECT"
        )
    pack_area = _table(decoder, root.get("pack_cards"), field="G.pack_cards")
    raw_choices = _strict_array_table_values(decoder, pack_area.get("cards"))
    if raw_choices is None or not raw_choices:
        raise LiveBuffoonPackParityCaptureError(
            "Buffoon pack choices are unavailable or malformed"
        )
    choices = tuple(
        _exact_choice_record(
            _normalize_item(decoder, address, area_index=area_index),
            area_index=area_index,
        )
        for area_index, (_, address) in enumerate(raw_choices)
    )
    return choices_remaining, return_phase, choices


def capture_live_buffoon_pack_parity_checkpoint(
    observer,
) -> LiveBuffoonPackParityCheckpoint:
    before = observer.observe()
    if not isinstance(before, LiveBalatroSnapshot):
        raise LiveBuffoonPackParityCaptureError(
            "observer did not return LiveBalatroSnapshot"
        )
    if before.phase != "BUFFOON_PACK" or before.state_complete is not True:
        raise LiveBuffoonPackParityCaptureError(
            "Buffoon parity checkpoint requires complete BUFFOON_PACK"
        )
    try:
        decoder, _, root = observer._root()
        first_terms = _private_pack_terms(decoder, root)
        after = observer.observe()
        decoder, _, root = observer._root()
        second_terms = _private_pack_terms(decoder, root)
    except (OSError, RuntimeError) as exc:
        if isinstance(exc, LiveBuffoonPackParityCaptureError):
            raise
        raise LiveBuffoonPackParityCaptureError(
            "unable to capture exact live Buffoon replay authority"
        ) from exc
    if before != after or first_terms != second_terms:
        raise LiveBuffoonPackParityCaptureError(
            "live Buffoon state changed while capturing replay authority"
        )
    checkpoint = LiveBuffoonPackParityCheckpoint(
        public_snapshot=deepcopy(before),
        choices_remaining=first_terms[0],
        return_phase=first_terms[1],
        choices=deepcopy(first_terms[2]),
    )
    headless_buffoon_pack_run_from_checkpoint(checkpoint)
    return checkpoint


def headless_buffoon_pack_run_from_checkpoint(
    checkpoint: LiveBuffoonPackParityCheckpoint,
    *,
    translator: DefaultBalatroStateTranslator | None = None,
) -> HeadlessRunState:
    if not isinstance(checkpoint, LiveBuffoonPackParityCheckpoint):
        raise TypeError("checkpoint must be LiveBuffoonPackParityCheckpoint")
    if checkpoint.public_snapshot.phase != "BUFFOON_PACK":
        raise LiveBuffoonPackParityCaptureError(
            "headless Buffoon restoration requires BUFFOON_PACK"
        )
    if checkpoint.choices_remaining != 1:
        raise LiveBuffoonPackParityCaptureError(
            "headless Buffoon restoration requires one remaining pick"
        )
    if checkpoint.return_phase not in {"SHOP", "BLIND_SELECT"}:
        raise LiveBuffoonPackParityCaptureError(
            "headless Buffoon restoration requires an exact return origin"
        )
    choices = []
    for index, raw in enumerate(checkpoint.choices):
        record = _exact_choice_record(raw, area_index=index)
        joker = LiveJokerFactory().create(record)
        if joker is None:
            raise LiveBuffoonPackParityCaptureError(
                "Buffoon checkpoint contains an unsupported Joker"
            )
        choices.append(joker)
    translator = translator or DefaultBalatroStateTranslator()
    public = translator.translate(checkpoint.public_snapshot)
    try:
        run = HeadlessRunState(
            public=public,
            seed="R5-BUFFOON-PACK-REPLAY",
            pack_choices=choices,
            pack_return_phase=checkpoint.return_phase,
            pack_choices_remaining=checkpoint.choices_remaining,
        )
    except (TypeError, ValueError, HeadlessTransitionError) as exc:
        raise LiveBuffoonPackParityCaptureError(
            "Buffoon checkpoint cannot restore exact headless authority"
        ) from exc
    if not all(can_choose_pack_option_exact(run, index) for index in range(len(choices))):
        raise LiveBuffoonPackParityCaptureError(
            "Buffoon choices are outside the exact inventory-only acquisition subset"
        )
    return run


def _action_for_checkpoint(checkpoint: LiveBuffoonPackParityCheckpoint, action) -> EnvAction:
    name = str(getattr(action, "name", ""))
    if tuple(getattr(action, "cards", ()) or ()):
        raise LiveBuffoonPackParityCaptureError(
            "Buffoon parity action must not select hand cards"
        )
    target = getattr(action, "target", None)
    if name == SKIP_BOOSTER:
        if target is not None:
            raise LiveBuffoonPackParityCaptureError("SKIP_BOOSTER must be parameterless")
        return EnvAction.from_alias("SKIP_PACK")
    if name != SELECT_PACK_CARD:
        raise LiveBuffoonPackParityCaptureError(
            "Buffoon parity accepts only SELECT_PACK_CARD or SKIP_BOOSTER"
        )
    read = target.get if isinstance(target, dict) else lambda key, default=None: getattr(target, key, default)
    index = read("area_index")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(checkpoint.choices):
        raise LiveBuffoonPackParityCaptureError("Buffoon selection index is not exact")
    choice = checkpoint.choices[index]
    label = read("label")
    data = read("data")
    if not isinstance(label, str) or label != choice.get("label"):
        raise LiveBuffoonPackParityCaptureError(
            "Buffoon selection label does not match captured choice"
        )
    if not isinstance(data, dict):
        raise LiveBuffoonPackParityCaptureError(
            "Buffoon selection requires exact live choice data"
        )
    if data.get("center") != choice.get("center"):
        raise LiveBuffoonPackParityCaptureError(
            "Buffoon selection center does not match captured choice"
        )
    raw_live_id = data.get("live_id")
    if isinstance(raw_live_id, float) and raw_live_id.is_integer():
        raw_live_id = int(raw_live_id)
    if raw_live_id != choice.get("live_id"):
        raise LiveBuffoonPackParityCaptureError(
            "Buffoon selection live_id does not match captured choice"
        )
    return EnvAction.from_alias("CHOOSE_PACK_OPTION", {"option_index": index})


def compare_captured_live_buffoon_pack(
    before: LiveBuffoonPackParityCheckpoint,
    action,
    after_snapshot: LiveBalatroSnapshot,
) -> LiveBuffoonPackReplayComparison:
    run = headless_buffoon_pack_run_from_checkpoint(before)
    canonical_action = _action_for_checkpoint(before, action)
    if after_snapshot.phase != before.return_phase or after_snapshot.state_complete is not True:
        raise LiveBuffoonPackParityCaptureError(
            "Buffoon action did not settle at its exact return origin"
        )
    live_after = DefaultBalatroStateTranslator().translate(after_snapshot)
    live_evidence = build_public_strategic_transition_evidence(
        run.public,
        canonical_action,
        live_after,
    )
    try:
        if canonical_action.alias == "CHOOSE_PACK_OPTION":
            _, simulator_evidence = choose_pack_option_with_public_evidence(
                run,
                option_index=canonical_action.payload()["option_index"],
            )
        else:
            _, simulator_evidence = skip_pack_with_public_evidence(run)
    except HeadlessTransitionError as exc:
        raise LiveBuffoonPackParityCaptureError(
            f"Buffoon checkpoint does not admit exact replay: {exc}"
        ) from exc
    public = compare_public_strategic_evidence(live_evidence, simulator_evidence)
    differences = tuple(f"public.{item}" for item in public.differences)
    return LiveBuffoonPackReplayComparison(
        matches=not differences,
        differences=differences,
        public=public,
    )


def _snapshot_to_payload(snapshot: LiveBalatroSnapshot) -> dict[str, Any]:
    return {
        "sequence": int(snapshot.sequence),
        "phase": str(snapshot.phase),
        "state_complete": bool(snapshot.state_complete),
        "payload": deepcopy(snapshot.payload),
    }


def _snapshot_from_payload(payload: dict[str, Any]) -> LiveBalatroSnapshot:
    if not isinstance(payload, dict) or not isinstance(payload.get("payload"), dict):
        raise LiveBuffoonPackParityCaptureError("public snapshot payload is malformed")
    phase = payload.get("phase")
    complete = payload.get("state_complete")
    if not isinstance(phase, str) or not phase or not isinstance(complete, bool):
        raise LiveBuffoonPackParityCaptureError("public snapshot metadata is malformed")
    return LiveBalatroSnapshot(
        sequence=_exact_nonnegative_int(payload.get("sequence"), field="sequence"),
        phase=phase,
        state_complete=complete,
        payload=deepcopy(payload["payload"]),
    )


def buffoon_pack_parity_checkpoint_to_payload(
    checkpoint: LiveBuffoonPackParityCheckpoint,
) -> dict[str, Any]:
    if not isinstance(checkpoint, LiveBuffoonPackParityCheckpoint):
        raise TypeError("checkpoint must be LiveBuffoonPackParityCheckpoint")
    return {
        "public_snapshot": _snapshot_to_payload(checkpoint.public_snapshot),
        "choices_remaining": checkpoint.choices_remaining,
        "return_phase": checkpoint.return_phase,
        "choices": deepcopy(list(checkpoint.choices)),
    }


def buffoon_pack_parity_checkpoint_from_payload(
    payload: dict[str, Any],
) -> LiveBuffoonPackParityCheckpoint:
    if not isinstance(payload, dict):
        raise LiveBuffoonPackParityCaptureError("Buffoon checkpoint must be a mapping")
    raw_choices = payload.get("choices")
    if not isinstance(raw_choices, list) or not raw_choices:
        raise LiveBuffoonPackParityCaptureError("Buffoon checkpoint choices are malformed")
    checkpoint = LiveBuffoonPackParityCheckpoint(
        public_snapshot=_snapshot_from_payload(payload.get("public_snapshot")),
        choices_remaining=_exact_nonnegative_int(
            payload.get("choices_remaining"), field="choices_remaining"
        ),
        return_phase=str(payload.get("return_phase") or ""),
        choices=tuple(
            _exact_choice_record(choice, area_index=index)
            for index, choice in enumerate(raw_choices)
        ),
    )
    headless_buffoon_pack_run_from_checkpoint(checkpoint)
    return checkpoint


class LiveBuffoonPackParityRecorder:
    SCHEMA = "balatro-r5-buffoon-pack-parity-v1"

    def __init__(self, run_id: str, observer, *, directory: str | Path) -> None:
        normalized = str(run_id).strip()
        if not normalized or normalized in {".", ".."} or "/" in normalized or "\\" in normalized:
            raise ValueError("Buffoon parity run_id is invalid")
        self.run_id = normalized
        self.observer = observer
        self.directory = Path(directory)
        self.path = self.directory / f"{self.run_id}.buffoon-pack-parity.jsonl"
        self._sequence = self._existing_sequence()

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
                raise LiveBuffoonPackParityCaptureError(
                    f"invalid Buffoon parity JSON at {self.path}:{line_number}"
                ) from exc
            expected = sequence + 1
            if (
                row.get("schema") != self.SCHEMA
                or str(row.get("run_id")) != self.run_id
                or row.get("sequence") != expected
            ):
                raise LiveBuffoonPackParityCaptureError(
                    f"unexpected Buffoon parity row at {self.path}:{line_number}"
                )
            sequence = expected
        return sequence

    def capture_before(self, decision) -> LiveBuffoonPackParityCheckpoint:
        checkpoint = capture_live_buffoon_pack_parity_checkpoint(self.observer)
        if not _same_snapshot(decision.snapshot, checkpoint.public_snapshot):
            raise LiveBuffoonPackParityCaptureError(
                "planned Buffoon snapshot does not match private checkpoint"
            )
        _action_for_checkpoint(checkpoint, decision.action)
        return checkpoint

    def record_after(self, before, decision, dispatch_result) -> LiveBuffoonPackReplayComparison:
        if not _same_snapshot(decision.snapshot, dispatch_result.before):
            raise LiveBuffoonPackParityCaptureError(
                "settled Buffoon result does not begin at the planned snapshot"
            )
        planned_action = _action_for_checkpoint(before, decision.action)
        settled_action = _action_for_checkpoint(before, dispatch_result.action)
        if settled_action != planned_action:
            raise LiveBuffoonPackParityCaptureError(
                "settled Buffoon action does not match the planned action"
            )
        observed_after = self.observer.observe()
        if not _same_snapshot(dispatch_result.after, observed_after):
            raise LiveBuffoonPackParityCaptureError(
                "settled Buffoon result does not match current public state"
            )
        comparison = compare_captured_live_buffoon_pack(
            before,
            decision.action,
            observed_after,
        )
        canonical = planned_action
        self._sequence += 1
        row = {
            "schema": self.SCHEMA,
            "run_id": self.run_id,
            "sequence": self._sequence,
            "action": {
                "name": canonical.action_id,
                **canonical.payload(),
            },
            "before": buffoon_pack_parity_checkpoint_to_payload(before),
            "after_public_snapshot": _snapshot_to_payload(observed_after),
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
