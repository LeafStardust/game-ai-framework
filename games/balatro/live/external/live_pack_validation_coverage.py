from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


RUN_EVENT_SCHEMA = "balatro-run-experience-v1"
DEFAULT_RUN_LOG_DIRECTORY = Path("logs/balatro/runs")

D9_REQUIRED_FAMILIES = (
    "JOKER",
    "STANDARD",
    "PLANET",
    "TAROT",
    "SPECTRAL",
)
D10_REQUIRED_FLOWS = (
    "STANDARD_SELECTION",
    "TAROT_TARGETED",
    "SPECTRAL_TARGETED",
)

PACK_PHASE_FAMILY = {
    "BUFFOON_PACK": "JOKER",
    "STANDARD_PACK": "STANDARD",
    "CELESTIAL_PACK": "PLANET",
    "PLANET_PACK": "PLANET",
    "TAROT_PACK": "TAROT",
    "ARCANA_PACK": "TAROT",
    "SPECTRAL_PACK": "SPECTRAL",
}

PACK_ACTIONS = frozenset({"SELECT_PACK_CARD", "SKIP_BOOSTER"})


def _load_run_rows(path: Path) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    expected_run_id: str | None = None
    expected_sequence = 1

    for line_number, raw in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"invalid Balatro run JSONL at {path}:{line_number}: {error}"
            ) from error
        if not isinstance(row, dict) or row.get("schema") != RUN_EVENT_SCHEMA:
            raise ValueError(
                f"unexpected Balatro run schema at {path}:{line_number}"
            )

        run_id = str(row.get("run_id") or "")
        if not run_id:
            raise ValueError(f"missing run_id at {path}:{line_number}")
        if expected_run_id is None:
            expected_run_id = run_id
        elif run_id != expected_run_id:
            raise ValueError(
                f"mixed run_id values in {path}: {expected_run_id!r} and {run_id!r}"
            )

        sequence = row.get("sequence")
        if isinstance(sequence, bool) or not isinstance(sequence, int):
            raise ValueError(f"invalid event sequence at {path}:{line_number}")
        if sequence != expected_sequence:
            raise ValueError(
                f"non-contiguous event sequence in {path}: expected "
                f"{expected_sequence}, observed {sequence}"
            )
        expected_sequence += 1
        rows.append(row)

    return tuple(rows)


def _state_is_authoritative_process_memory(state: object) -> bool:
    if not isinstance(state, dict) or state.get("state_complete") is not True:
        return False
    payload = state.get("payload")
    return (
        isinstance(payload, dict)
        and payload.get("live_state_source") == "process_memory"
    )


def _checkpoint_sequence(state: dict[str, Any]) -> int | None:
    value = state.get("sequence")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _notes(decision_data: dict[str, Any]) -> tuple[str, ...]:
    rationale = decision_data.get("rationale")
    if not isinstance(rationale, dict):
        return ()
    values = rationale.get("notes")
    if not isinstance(values, list):
        return ()
    return tuple(str(value) for value in values)


def _decision_source(decision_data: dict[str, Any]) -> str:
    rationale = decision_data.get("rationale")
    if not isinstance(rationale, dict):
        return ""
    return str(rationale.get("decision_source") or "")


def _action(decision_data: dict[str, Any]) -> dict[str, Any]:
    value = decision_data.get("action")
    return value if isinstance(value, dict) else {}


def _successful_pack_transitions(
    rows: Iterable[dict[str, Any]],
) -> Iterable[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    observation_row: dict[str, Any] | None = None
    decision_row: dict[str, Any] | None = None

    for row in rows:
        event = str(row.get("event") or "")
        data = row.get("data")
        data = data if isinstance(data, dict) else {}

        if event == "observation":
            observation_row = row
            decision_row = None
            continue

        if event == "decision" and observation_row is not None:
            decision_row = row
            continue

        if event != "action_result" or observation_row is None or decision_row is None:
            continue

        observation_data = observation_row.get("data")
        observation_data = observation_data if isinstance(observation_data, dict) else {}
        decision_data = decision_row.get("data")
        decision_data = decision_data if isinstance(decision_data, dict) else {}
        result_data = data

        before = observation_data.get("state")
        after = result_data.get("state")
        action = _action(decision_data)
        result_action = result_data.get("action")
        result_action = result_action if isinstance(result_action, dict) else {}

        valid = (
            result_data.get("success") is True
            and _state_is_authoritative_process_memory(before)
            and _state_is_authoritative_process_memory(after)
            and _decision_source(decision_data) == "pack policy"
            and str(action.get("name") or "") in PACK_ACTIONS
            and str(result_action.get("name") or "") == str(action.get("name") or "")
        )
        if valid:
            before_sequence = _checkpoint_sequence(before)
            after_sequence = _checkpoint_sequence(after)
            if (
                before_sequence is not None
                and after_sequence is not None
                and after_sequence > before_sequence
            ):
                yield observation_row, decision_row, row

        observation_row = None
        decision_row = None


def _base_evidence(
    observation_row: dict[str, Any],
    decision_row: dict[str, Any],
    result_row: dict[str, Any],
) -> dict[str, Any]:
    observation_data = observation_row["data"]
    decision_data = decision_row["data"]
    result_data = result_row["data"]
    before = observation_data["state"]
    after = result_data["state"]
    action = _action(decision_data)
    return {
        "run_id": str(decision_row.get("run_id") or ""),
        "phase": str(before.get("phase") or ""),
        "action": str(action.get("name") or ""),
        "target": action.get("target") if isinstance(action.get("target"), dict) else {},
        "target_indices": list(action.get("indices") or []),
        "notes": list(_notes(decision_data)),
        "before_checkpoint_sequence": int(before["sequence"]),
        "after_checkpoint_sequence": int(after["sequence"]),
        "decision_event_sequence": int(decision_row["sequence"]),
        "result_event_sequence": int(result_row["sequence"]),
        "postcondition_verified": True,
        "live_state_source": "process_memory",
    }


def _has_b6_target_rationale(notes: tuple[str, ...]) -> bool:
    return any(
        note.startswith("B6 ") and "target" in note.lower()
        for note in notes
    )


def _has_standard_build_rationale(notes: tuple[str, ...]) -> bool:
    return any("B6 playing-card build gain=" in note for note in notes)


def _coverage(required: tuple[str, ...], evidence: list[dict[str, Any]], key: str) -> dict[str, Any]:
    observed = tuple(
        item
        for item in required
        if any(record.get(key) == item for record in evidence)
    )
    missing = tuple(item for item in required if item not in observed)
    return {
        "required": required,
        "observed": observed,
        "missing": missing,
        "complete": not missing,
        "evidence": tuple(evidence),
    }


def analyze_run_logs(
    directory: str | Path = DEFAULT_RUN_LOG_DIRECTORY,
) -> dict[str, Any]:
    """Derive D9/D10 live validation evidence from successful production run logs.

    ``log_successful_live_transition`` writes ``action_result`` only after the
    first-party injected dispatcher has returned a settled authoritative
    postcondition. Targeted Tarot/Spectral ``SELECT_PACK_CARD`` actions therefore
    count only when the logged decision contains concrete hand target indices; the
    dispatcher contract verifies those target semantics before the successful row
    can exist. Standard packs are intentionally treated as their documented
    one-stage offer-selection flow, not fabricated as a second-target action.
    """
    root = Path(directory)
    d9_evidence: list[dict[str, Any]] = []
    d10_evidence: list[dict[str, Any]] = []

    for path in sorted(root.glob("*.jsonl")) if root.exists() else ():
        rows = _load_run_rows(path)
        for observation_row, decision_row, result_row in _successful_pack_transitions(rows):
            before = observation_row["data"]["state"]
            decision_data = decision_row["data"]
            phase = str(before.get("phase") or "")
            family = PACK_PHASE_FAMILY.get(phase)
            if family is None:
                continue

            base = _base_evidence(observation_row, decision_row, result_row)
            d9_evidence.append({**base, "family": family})

            action = _action(decision_data)
            if str(action.get("name") or "") != "SELECT_PACK_CARD":
                continue
            notes = _notes(decision_data)
            indices = action.get("indices")
            indices = indices if isinstance(indices, list) else []

            flow: str | None = None
            if family == "STANDARD" and _has_standard_build_rationale(notes):
                target = action.get("target")
                if isinstance(target, dict) and isinstance(target.get("area_index"), int):
                    flow = "STANDARD_SELECTION"
            elif family == "TAROT" and indices and _has_b6_target_rationale(notes):
                flow = "TAROT_TARGETED"
            elif family == "SPECTRAL" and indices and _has_b6_target_rationale(notes):
                flow = "SPECTRAL_TARGETED"

            if flow is not None:
                d10_evidence.append({**base, "flow": flow})

    return {
        "run_log_directory": str(root),
        "d9": _coverage(D9_REQUIRED_FAMILIES, d9_evidence, "family"),
        "d10": _coverage(D10_REQUIRED_FLOWS, d10_evidence, "flow"),
    }


def _print_coverage(name: str, coverage: dict[str, Any]) -> None:
    print(f"{name} observed -> {', '.join(coverage['observed']) or '<none>'}")
    print(f"{name} missing -> {', '.join(coverage['missing']) or '<none>'}")
    print(f"{name} complete -> {coverage['complete']}")
    for record in coverage["evidence"]:
        label = record.get("family") or record.get("flow") or "UNKNOWN"
        print(
            f"  evidence {label}: run={record['run_id']} "
            f"phase={record['phase']} action={record['action']} "
            f"checkpoint={record['before_checkpoint_sequence']}"
            f"->{record['after_checkpoint_sequence']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read existing successful Balatro production run logs and report "
            "authoritative D9 pack-family and D10 pack-flow live validation coverage."
        )
    )
    parser.add_argument(
        "--run-log-directory",
        type=Path,
        default=DEFAULT_RUN_LOG_DIRECTORY,
    )
    args = parser.parse_args()

    report = analyze_run_logs(args.run_log_directory)
    print("Live pack validation coverage -> ANALYZED")
    print(f"Run log directory -> {report['run_log_directory']}")
    _print_coverage("D9", report["d9"])
    _print_coverage("D10", report["d10"])
    print("Gameplay action executed -> False")
    print("Hidden RNG/deck traversal -> False")
    return 0 if report["d9"]["complete"] and report["d10"]["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
