"""Audit a recorded capture for reader errors, missing steps, calls and lifecycle."""

import argparse
from collections import Counter
import json
from pathlib import Path

from games.mahjong_soul.live.external.schema import LiqiSchema
from games.mahjong_soul.live.runtime.monitor import CaptureTail
from games.mahjong_soul.live.runtime.reader import GameReader


def audit(rows, schema, seat=None):
    reader = GameReader(schema, seat)
    rounds = {}
    match_ids = {}
    connection_matches = {}
    issues = Counter()
    calls = Counter()
    malformed = 0
    for row in rows:
        try:
            result = reader.consume(row)
        except (ValueError, KeyError, TypeError):
            malformed += 1
            continue
        decoded = result.get("liqi", {})
        if decoded.get("method") == ".lq.FastTest.authGame" and decoded.get("kind") == "request":
            game_id = decoded.get("data", {}).get("game_uuid")
            if game_id:
                connection_matches[row["connection"]] = match_ids.setdefault(game_id, len(match_ids) + 1)
        for event in decoded.get("events", []):
            if event["name"] == "ActionMJStart":
                continue
            state = result["state"]
            match = connection_matches.get(row["connection"], 1)
            meta = state["round"]
            key = (match, meta.get("chang", 0), meta.get("ju", 0), meta.get("ben", 0))
            entry = rounds.setdefault(key, {"match": match, "round": dict(meta), "steps": {}, "duplicates": 0,
                                           "conflicts": [], "end": None, "calls": Counter()})
            core = {name: event["data"][name] for name in ("seat", "tile", "tiles", "froms", "type", "scores", "doras") if name in event["data"]}
            fingerprint = json.dumps([event["name"], core], sort_keys=True)
            step = event["step"]
            if step in entry["steps"]:
                entry["duplicates"] += 1
                if entry["steps"][step] != fingerprint:
                    entry["conflicts"].append(step)
            else:
                entry["steps"][step] = fingerprint
                if event["name"] in ("ActionChiPengGang", "ActionAnGangAddGang", "ActionBaBei"):
                    label = event["name"] + ":" + str(event["data"].get("type", "north"))
                    entry["calls"][label] += 1
                    calls[label] += 1
            if event["name"] in ("ActionHule", "ActionNoTile", "ActionLiuJu"):
                entry["end"] = {"action": event["name"], "scores": list(state["scores"])}
            issues.update(state["issues"])
    summaries = []
    for entry in rounds.values():
        steps = sorted(entry.pop("steps"))
        entry["actions"] = len(steps)
        entry["gaps"] = sorted(set(range(steps[0], steps[-1] + 1)) - set(steps)) if steps else []
        entry["first_step"] = steps[0] if steps else None
        entry["last_step"] = steps[-1] if steps else None
        entry["calls"] = dict(entry["calls"])
        summaries.append(entry)
    latest = reader.snapshot()
    state = latest["state"]
    coherent = bool(state) and state["status"] != "incomplete" and not malformed and not latest["decode_errors"] and not issues
    coherent = coherent and all(not item["gaps"] and not item["conflicts"] for item in summaries)
    return {"coherent": coherent, "match_ended": bool(state and state["status"] == "match_ended"),
            "frames": latest["frames"], "malformed_rows": malformed, "rounds": summaries,
            "calls": dict(calls), "decode_errors": latest["decode_errors"], "schema_warnings": latest["schema_warnings"],
            "historical_state_issues": dict(issues), "latest_state": state}


def main():
    root = Path(__file__).resolve().parents[4]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture")
    parser.add_argument("--schema", default=str(root / "liqi-reference.json"))
    parser.add_argument("--seat", type=int, choices=range(4))
    parser.add_argument("--strict", action="store_true", help="Exit nonzero if game data is incoherent")
    args = parser.parse_args()
    if not Path(args.capture).is_file():
        parser.error("capture file does not exist")
    tail = CaptureTail(args.capture)
    result = audit(tail.read(), LiqiSchema.load(args.schema), args.seat)
    result["malformed_rows"] += tail.bad_rows
    if tail.bad_rows:
        result["coherent"] = False
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if args.strict and not result["coherent"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
