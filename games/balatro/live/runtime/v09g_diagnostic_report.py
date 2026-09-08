from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


DIAGNOSTIC_SCHEMA = "balatro-diagnostic-v1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _resolve_directory(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else _repo_root() / path


def _load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError(f"expected JSON object at {path}:{line_number}")
        rows.append(value)
    return rows


def _is_recovered_stale_replan(row: dict[str, Any]) -> bool:
    if str(row.get("stage") or "") != "execution_failure":
        return False
    data = row.get("data")
    if not isinstance(data, dict):
        return False
    return (
        str(data.get("error_type") or "") == "AutonomousStepGuardError"
        and "live state changed after autonomous planning" in str(data.get("error") or "")
    )


def _short(value: object, limit: int = 160) -> str:
    text = str(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def render(session_id: str, rows: list[dict[str, Any]]) -> str:
    schema_errors = sum(1 for row in rows if row.get("schema") != DIAGNOSTIC_SCHEMA)
    session_errors = sum(1 for row in rows if str(row.get("session_id") or "") != session_id)
    expected = list(range(1, len(rows) + 1))
    observed = [row.get("sequence") for row in rows]
    sequence_ok = observed == expected

    recovered = [row for row in rows if _is_recovered_stale_replan(row)]
    actionable = [row for row in rows if not _is_recovered_stale_replan(row)]

    stage_counts = Counter(str(row.get("stage") or "UNKNOWN") for row in rows)
    error_counts = Counter()
    for row in rows:
        data = row.get("data")
        if isinstance(data, dict):
            error_counts[str(data.get("error_type") or "UNKNOWN")] += 1
        else:
            error_counts["UNKNOWN"] += 1

    lines = [
        "=" * 78,
        "BALATRO v0.9G DIAGNOSTIC CLASSIFICATION",
        "=" * 78,
        f"Session                         : {session_id}",
        f"Total diagnostic events         : {len(rows)}",
        f"Recovered stale replans         : {len(recovered)}",
        f"Actionable failure/block events : {len(actionable)}",
        f"Schema/session/sequence          : {'PASS' if not schema_errors and not session_errors and sequence_ok else 'FAIL'}",
        "",
        "STAGE COUNTS",
        "-" * 78,
    ]
    lines.extend(f"{stage:<32} : {count}" for stage, count in sorted(stage_counts.items()))
    lines.extend(["", "ERROR TYPE COUNTS", "-" * 78])
    lines.extend(f"{name:<32} : {count}" for name, count in sorted(error_counts.items()))

    if actionable:
        lines.extend(["", "ACTIONABLE EVENTS", "-" * 78])
        for row in actionable:
            data = row.get("data") if isinstance(row.get("data"), dict) else {}
            lines.append(
                f"#{row.get('sequence')} {row.get('stage')} | "
                f"{data.get('error_type')}: {_short(data.get('error'))} | "
                f"phase={data.get('phase')} action={data.get('action')}"
            )

    if schema_errors or session_errors or not sequence_ok:
        overall = "FAIL — diagnostic artifact integrity is invalid"
    elif actionable:
        overall = "REVIEW — genuine diagnostic events remain"
    else:
        overall = "PASS — all diagnostics are recovered stale-state replans"

    lines.extend(["", f"Overall                         : {overall}"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Classify Balatro v0.9G diagnostic events for one live session."
    )
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--diagnostic-directory", default="logs/balatro/diagnostics")
    args = parser.parse_args()

    directory = _resolve_directory(args.diagnostic_directory)
    path = directory / f"{args.session_id}.jsonl"
    try:
        rows = _load_rows(path)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print("Balatro v0.9G diagnostic report -> FAIL")
        print(f"Reason -> {error}")
        return 2

    print(render(str(args.session_id), rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
