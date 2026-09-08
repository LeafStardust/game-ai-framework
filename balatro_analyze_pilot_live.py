from __future__ import annotations

"""Summarize one completed three-Bond pilot live batch for causal diagnosis.

The analyzer is intentionally read-only. It consumes the durable report/run logs
produced by ``balatro_validate_pilot_live.py`` and surfaces evidence needed to find
the first wrong architecture stage before any numerical tuning.
"""

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


_DEFAULT_ROOT = Path("logs/balatro/pilot-live")
_PILOT_TOKENS = {
    "BURNT": ("burnt", "burnt_target_level"),
    "DECK_THINNING": ("deck_thinning",),
    "HELD_CARD": ("baron_mime_steel", "held_cards", "held_retrigger"),
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object in {path}")
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError(f"expected JSON object at {path}:{line_number}")
        rows.append(value)
    return rows


def _decision_data(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    data = row.get("data") if isinstance(row.get("data"), dict) else {}
    rationale = data.get("rationale") if isinstance(data.get("rationale"), dict) else {}
    postmortem = rationale.get("postmortem") if isinstance(rationale.get("postmortem"), dict) else {}
    bond_strategy = postmortem.get("bond_strategy") if isinstance(postmortem.get("bond_strategy"), dict) else {}
    notes = rationale.get("notes") if isinstance(rationale.get("notes"), list) else []
    return data, bond_strategy, [str(note) for note in notes]


def _strategy_text(bond_strategy: dict[str, Any]) -> str:
    parts: list[str] = []
    pinned = bond_strategy.get("pinned_strategy")
    if pinned:
        parts.append(str(pinned))
    for candidate in bond_strategy.get("strategy_candidates", ()):
        if not isinstance(candidate, dict):
            continue
        parts.extend(
            str(value)
            for value in (
                candidate.get("strategy_id"),
                *tuple(candidate.get("bond_ids", ()) or ()),
                *tuple(candidate.get("motif_ids", ()) or ()),
            )
            if value
        )
    for bond in bond_strategy.get("relevant_bonds", ()):
        if isinstance(bond, dict) and bond.get("bond_id"):
            parts.append(str(bond["bond_id"]))
    plan = bond_strategy.get("strategy_plan")
    if isinstance(plan, dict):
        parts.extend(
            str(value)
            for value in (
                plan.get("strategy_id"),
                *tuple(plan.get("missing_features", ()) or ()),
                *tuple(plan.get("missing_components", ()) or ()),
                *tuple(plan.get("prescriptions", ()) or ()),
            )
            if value
        )
    return " ".join(parts).lower()


def _pilot_hits(bond_strategy: dict[str, Any]) -> set[str]:
    text = _strategy_text(bond_strategy)
    return {
        label
        for label, tokens in _PILOT_TOKENS.items()
        if any(token in text for token in tokens)
    }


def _commitments(bond_strategy: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for candidate in bond_strategy.get("strategy_candidates", ()):
        if not isinstance(candidate, dict):
            continue
        strategy_id = candidate.get("strategy_id")
        commitment = candidate.get("commitment")
        if strategy_id and commitment:
            values.append(f"{strategy_id}:{commitment}")
    return values


def _short_action(data: dict[str, Any]) -> str:
    action = data.get("action")
    phase = data.get("phase")
    ante = data.get("ante")
    blind = data.get("blind") or data.get("blind_type")
    pieces = [
        f"ante={ante}" if ante is not None else None,
        f"phase={phase}" if phase is not None else None,
        f"blind={blind}" if blind is not None else None,
        f"action={action}" if action is not None else None,
    ]
    return " ".join(piece for piece in pieces if piece) or "decision"


def _last_nonempty_notes(notes: list[str], *, limit: int = 2) -> str:
    selected = [note.strip() for note in notes if note.strip()][-limit:]
    text = " | ".join(selected)
    return text if len(text) <= 360 else text[:357] + "..."


def _run_summary(run_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = [row for row in rows if row.get("event") == "decision"]
    pilots: set[str] = set()
    commitments: set[str] = set()
    plan_count = 0
    decision_trail: list[str] = []

    for row in decisions:
        data, bond_strategy, notes = _decision_data(row)
        pilots.update(_pilot_hits(bond_strategy))
        commitments.update(_commitments(bond_strategy))
        if isinstance(bond_strategy.get("strategy_plan"), dict):
            plan_count += 1
        decision_trail.append(
            _short_action(data)
            + ((" :: " + _last_nonempty_notes(notes)) if notes else "")
        )

    terminal = rows[-1] if rows else {}
    terminal_data = terminal.get("data") if isinstance(terminal.get("data"), dict) else {}
    terminal_event = str(terminal.get("event") or "UNKNOWN")
    ante = terminal_data.get("ante")
    if ante is None:
        for row in reversed(rows):
            data = row.get("data") if isinstance(row.get("data"), dict) else {}
            if data.get("ante") is not None:
                ante = data.get("ante")
                break

    return {
        "run_id": run_id,
        "terminal_event": terminal_event,
        "ante": ante,
        "decision_count": len(decisions),
        "pilots": sorted(pilots),
        "commitments": sorted(commitments),
        "strategy_plan_decisions": plan_count,
        "decision_trail": decision_trail[-5:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze the latest three-Bond live pilot batch.")
    parser.add_argument("--input-directory", type=Path, default=_DEFAULT_ROOT)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    root = args.input_directory
    report_path = args.report or (root / "latest-report.json")
    try:
        report = _load_json(report_path)
        run_ids = [str(value) for value in report.get("run_ids", ())]
        if not run_ids:
            raise ValueError("pilot report contains no run IDs")
        summaries = [
            _run_summary(run_id, _load_jsonl(root / "runs" / f"{run_id}.jsonl"))
            for run_id in run_ids
        ]
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print("Balatro three-Bond pilot postmortem -> FAIL")
        print(f"Reason -> {error}")
        return 2

    pilot_counts = Counter(pilot for summary in summaries for pilot in summary["pilots"])
    ante_counts = Counter(str(summary["ante"]) for summary in summaries)

    print("=" * 88)
    print("BALATRO THREE-BOND PILOT LIVE POSTMORTEM")
    print("=" * 88)
    print(f"Session -> {report.get('session_id', '?')}")
    print(f"Runs -> {len(summaries)}")
    print(f"Won -> {bool(report.get('won'))}")
    print(f"Ante distribution -> {dict(sorted(ante_counts.items()))}")
    print(f"Pilot opportunity/recognition counts -> {dict(sorted(pilot_counts.items()))}")
    print()

    for index, summary in enumerate(summaries, 1):
        print(f"[{index:02d}] {summary['run_id']}")
        print(
            f"  terminal={summary['terminal_event']} ante={summary['ante']} "
            f"decisions={summary['decision_count']} plans={summary['strategy_plan_decisions']}"
        )
        print(f"  pilots={','.join(summary['pilots']) if summary['pilots'] else 'NONE'}")
        if summary["commitments"]:
            print(f"  strategies={'; '.join(summary['commitments'])}")
        print("  final decision trail:")
        for item in summary["decision_trail"]:
            print(f"    - {item}")
        print()

    if not pilot_counts:
        print("Primary evidence -> no pilot strategy appeared in any of the 10 runs.")
        print("Next ownership question -> opportunity frequency / acquisition construction, not D1 preservation.")
    else:
        print("Primary evidence -> pilot strategy state appeared; inspect the per-run final trails above.")
        print("Next ownership question -> first bad decision after strategy recognition, before numerical tuning.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
