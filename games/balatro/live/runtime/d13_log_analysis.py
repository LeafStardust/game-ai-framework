from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


D13_SOURCE = "D13 contextual blind play-vs-skip policy"


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return float(default)
    return float(value)


def _integer(value: object, default: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return int(default)
    return int(value)


def read_run_rows(path: str | Path) -> list[dict[str, Any]]:
    log_path = Path(path)
    if not log_path.exists():
        raise FileNotFoundError(log_path)

    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(
        log_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"invalid JSON at {log_path}:{line_number}"
            ) from error
        if not isinstance(row, dict):
            raise ValueError(f"non-object row at {log_path}:{line_number}")
        if row.get("schema") != "balatro-run-experience-v1":
            raise ValueError(f"unexpected schema at {log_path}:{line_number}")
        rows.append(row)
    return rows


def analyze_d13_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latest_observation: dict[str, Any] = {}
    decisions: list[dict[str, Any]] = []

    for row in rows:
        event = str(row.get("event") or "")
        data = _dict(row.get("data"))

        if event == "observation":
            latest_observation = _dict(data.get("state"))
            continue
        if event != "decision":
            continue

        rationale = _dict(data.get("rationale"))
        postmortem = _dict(rationale.get("postmortem"))
        if str(postmortem.get("layer") or "") != "D13":
            continue
        if str(rationale.get("decision_source") or "") != D13_SOURCE:
            continue

        selected = _dict(postmortem.get("selected"))
        action = _dict(data.get("action"))
        observed_payload = _dict(latest_observation.get("payload"))
        observed_blind = _dict(observed_payload.get("blind"))

        margin = _number(selected.get("margin"))
        threshold = _number(selected.get("threshold"))
        decisions.append(
            {
                "event_sequence": _integer(row.get("sequence")),
                "checkpoint_sequence": _integer(latest_observation.get("sequence")),
                "ante": _integer(
                    observed_payload.get("ante_num", observed_payload.get("ante", 0))
                ),
                "money": _integer(observed_payload.get("money")),
                "blind_type": str(
                    selected.get("blind_type")
                    or observed_blind.get("type")
                    or "UNKNOWN"
                ).upper(),
                "tag_key": selected.get("tag_key", observed_blind.get("tag")),
                "action": str(action.get("name") or selected.get("action") or ""),
                "build_readiness": _number(selected.get("build_readiness")),
                "play_ev": _number(selected.get("play_ev")),
                "skip_ev": _number(selected.get("skip_ev")),
                "margin": margin,
                "threshold": threshold,
                "distance_to_skip": threshold - margin,
            }
        )

    ranked = sorted(
        decisions,
        key=lambda item: (float(item["margin"]), int(item["event_sequence"])),
        reverse=True,
    )
    executed_skips = [item for item in decisions if item["action"] == "SKIP_BLIND"]
    qualifying_selects = [
        item
        for item in decisions
        if item["action"] != "SKIP_BLIND"
        and float(item["margin"]) >= float(item["threshold"])
    ]

    best = ranked[0] if ranked else None
    return {
        "mode": "OFFLINE_D13_LOG_ANALYSIS",
        "d13_decision_count": len(decisions),
        "executed_skip_count": len(executed_skips),
        "policy_consistency_error_count": len(qualifying_selects),
        "best_opportunity": best,
        "top_opportunities": ranked[:10],
        "skip_was_offered_by_policy": bool(
            any(
                float(item["margin"]) >= float(item["threshold"])
                for item in decisions
            )
        ),
    }


def analyze_d13_log(path: str | Path) -> dict[str, Any]:
    result = analyze_d13_rows(read_run_rows(path))
    result["authoritative_log"] = str(Path(path))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze an existing authoritative Balatro JSONL run log and rank "
            "contextual D13 blind skip opportunities. No gameplay is performed."
        )
    )
    parser.add_argument("log_path")
    args = parser.parse_args()

    try:
        result = analyze_d13_log(args.log_path)
    except Exception as error:
        print("D13 log analysis -> FAIL")
        print(f"Reason -> {type(error).__name__}: {error}")
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
