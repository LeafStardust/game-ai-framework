"""Opt-in preservation of settled public BUY_JOKER parity fixtures.

Purchase parity needs no private sidecar: the canonical ``balatro-run-experience-v1``
rows already contain the public observation, chosen production action, and settled
post-action state.  This module only selects one coherent successful BUY_JOKER
boundary and writes those original rows unchanged.  It does not participate in
production policy choice, dispatch, or settlement.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from games.balatro.actions import BUY_JOKER
from games.balatro.live.parity_capture import successful_joker_purchase_evidence_from_run_rows


_RUN_SCHEMA = "balatro-run-experience-v1"


class JokerPurchaseFixtureError(ValueError):
    """Raised when a durable run log cannot yield one exact purchase fixture."""


def _read_canonical_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.is_file():
        raise JokerPurchaseFixtureError(f"purchase fixture source does not exist: {path}")

    rows: list[dict[str, Any]] = []
    raw_lines: list[str] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(keepends=True),
        start=1,
    ):
        if not raw_line.strip():
            continue
        try:
            row = json.loads(raw_line)
        except json.JSONDecodeError as error:
            raise JokerPurchaseFixtureError(
                f"invalid run-experience JSON at {path}:{line_number}"
            ) from error
        if not isinstance(row, dict):
            raise JokerPurchaseFixtureError(
                f"run-experience row must be an object at {path}:{line_number}"
            )
        if row.get("schema") != _RUN_SCHEMA:
            raise JokerPurchaseFixtureError(
                f"unexpected run-experience schema at {path}:{line_number}"
            )
        rows.append(row)
        raw_lines.append(raw_line)
    return rows, raw_lines


def _action_name(row: dict[str, Any]) -> str:
    data = row.get("data")
    if not isinstance(data, dict):
        return ""
    action = data.get("action")
    if not isinstance(action, dict):
        return ""
    return str(action.get("name") or "")


def _successful_purchase_boundaries(
    rows: list[dict[str, Any]],
) -> tuple[tuple[int, int, int], ...]:
    last_observation: int | None = None
    pending: tuple[int, int] | None = None
    boundaries: list[tuple[int, int, int]] = []

    for index, row in enumerate(rows):
        event = str(row.get("event") or "")

        if event == "observation":
            if pending is not None:
                raise JokerPurchaseFixtureError(
                    "BUY_JOKER decision was interrupted before its action_result"
                )
            data = row.get("data")
            if not isinstance(data, dict) or not isinstance(data.get("state"), dict):
                raise JokerPurchaseFixtureError("observation row requires state")
            last_observation = index
            continue

        if event == "decision":
            if pending is not None:
                raise JokerPurchaseFixtureError(
                    "BUY_JOKER decision was interrupted before its action_result"
                )
            if _action_name(row) == BUY_JOKER:
                if last_observation is None:
                    raise JokerPurchaseFixtureError(
                        "BUY_JOKER decision has no preceding observation"
                    )
                pending = (last_observation, index)
            continue

        if event != "action_result" or _action_name(row) != BUY_JOKER:
            continue

        if pending is None:
            raise JokerPurchaseFixtureError(
                "BUY_JOKER action_result has no captured decision boundary"
            )
        observation_index, decision_index = pending
        candidate = [
            rows[observation_index],
            rows[decision_index],
            row,
        ]
        try:
            evidence = successful_joker_purchase_evidence_from_run_rows(candidate)
        except ValueError as error:
            raise JokerPurchaseFixtureError(str(error)) from error
        if len(evidence) != 1:
            raise JokerPurchaseFixtureError(
                "BUY_JOKER candidate did not produce exactly one parity transition"
            )
        boundaries.append((observation_index, decision_index, index))
        pending = None

    if pending is not None:
        raise JokerPurchaseFixtureError(
            "BUY_JOKER decision has no settled action_result"
        )
    return tuple(boundaries)


def preserve_successful_joker_purchase_fixture(
    source: str | Path,
    destination: str | Path,
    *,
    occurrence: int = 0,
    overwrite: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Preserve one validated BUY_JOKER boundary using original run-log rows.

    ``occurrence`` is zero-based among successful supported BUY_JOKER transitions.
    The destination contains no wrapper or new schema: it is exactly the selected
    ``balatro-run-experience-v1`` observation/decision/action_result rows.
    """
    if isinstance(occurrence, bool) or not isinstance(occurrence, int) or occurrence < 0:
        raise ValueError("occurrence must be a nonnegative integer")

    source_path = Path(source)
    destination_path = Path(destination)
    if source_path.resolve() == destination_path.resolve():
        raise ValueError("source and destination must be different files")
    if destination_path.exists() and not overwrite:
        raise FileExistsError(destination_path)

    rows, raw_lines = _read_canonical_jsonl(source_path)
    boundaries = _successful_purchase_boundaries(rows)
    if occurrence >= len(boundaries):
        raise JokerPurchaseFixtureError(
            f"BUY_JOKER occurrence {occurrence} is unavailable; found {len(boundaries)}"
        )

    selected = boundaries[occurrence]
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_path.write_text(
        "".join(raw_lines[index] for index in selected),
        encoding="utf-8",
    )
    return tuple(rows[index] for index in selected)  # type: ignore[return-value]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preserve one successful canonical BUY_JOKER transition from a "
            "balatro-run-experience-v1 JSONL log for deterministic R5 replay."
        )
    )
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("--occurrence", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    rows = preserve_successful_joker_purchase_fixture(
        args.source,
        args.destination,
        occurrence=args.occurrence,
        overwrite=args.overwrite,
    )
    action = rows[1]["data"]["action"]
    print(
        "Preserved BUY_JOKER fixture -> "
        f"{args.destination} ({action.get('target', {}).get('label', 'unknown target')})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
