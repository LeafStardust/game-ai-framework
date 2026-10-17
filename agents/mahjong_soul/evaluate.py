"""Offline policy/contract coverage on recorded states; not a game simulator."""
import argparse
from collections import Counter
import json
from pathlib import Path
import time

from agents.mahjong_soul.policy import BaselinePolicy, proposal_from_policy, make_policy
from games.mahjong_soul.live.external.schema import LiqiSchema
from games.mahjong_soul.live.runtime.decision import decision_request, validate_proposal
from games.mahjong_soul.live.runtime.input import board_token
from games.mahjong_soul.live.runtime.monitor import CaptureTail
from games.mahjong_soul.live.runtime.reader import GameReader


def decide(policy, report, current_snapshot, *, clock=time.monotonic, ttl=2):
    """Validate the policy response against a re-read snapshot, without input."""
    request = decision_request(report, now=clock(), ttl=ttl)
    proposal = proposal_from_policy(policy, request)
    return validate_proposal(request, proposal, current_snapshot(), now=clock())


def evaluate_capture(rows, schema, policy=None, *, clock=time.monotonic):
    reader = GameReader(schema)
    policy = BaselinePolicy() if policy is None else policy
    seen = set(); choices = Counter(); unsupported = Counter(); failures = Counter()
    normalization_ok = 0; decision_failures = 0; malformed = 0
    for row in rows:
        try:
            reader.consume(row)
        except (ValueError, KeyError, TypeError):
            malformed += 1
            continue
        report = reader.snapshot(); state = report.get("state") or {}
        if (not report.get("state_ready") or not report.get("connection_open")
                or not (state.get("operations") or {}).get("operation_list")):
            continue
        token = board_token(report)
        if token in seen: continue
        seen.add(token)
        try:
            request = decision_request(report, now=clock())
        except ValueError as error:
            unsupported[str(error)] += 1
            continue
        normalization_ok += 1
        try:
            proposal = proposal_from_policy(policy, request)
            validated = validate_proposal(request, proposal, reader.snapshot(), now=clock())
        except Exception as error:
            # A failed policy is a measured failure, never a fallback input.
            decision_failures += 1
            failures[type(error).__name__] += 1
            continue
        choices[validated["action"]["kind"]] += 1
    final = reader.snapshot()
    return {"version":1,"mode":"offline_contract_evaluation","executable":False,
            "policy":type(policy).__name__,"frames":final["frames"],
            "unique_decision_boards":len(seen),"normalized_requests":normalization_ok,
            "validated_proposals":sum(choices.values()),"chosen_actions":dict(choices),
            "unsupported_requests":dict(unsupported),"policy_failures":decision_failures,
            "policy_failure_types":dict(failures),"malformed_rows":malformed,
            "decode_error_count":sum(e["count"] for e in final["decode_errors"]),
            "connection_open_at_end":final["connection_open"],
            "limitation":"Recorded states are not counterfactual games; no strength or win-rate measurement."}


def main():
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--policy", choices=["baseline","efficiency"], default="efficiency")
    parser.add_argument("--schema", type=Path, default=root / "liqi-reference.json")
    parser.add_argument("--output", type=Path, help="Create a new aggregate report; refuses existing paths")
    args = parser.parse_args()
    if not args.capture.is_file(): parser.error("Capture does not exist")
    if args.output and args.output.exists(): parser.error("Output exists; choose a new path")
    tail = CaptureTail(args.capture)
    result = evaluate_capture(tail.read(), LiqiSchema.load(args.schema), make_policy(args.policy))
    result["malformed_rows"] += tail.bad_rows
    result["unfinished_capture_row"] = bool(tail.pending)
    encoded = json.dumps(result, indent=2)+"\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream: stream.write(encoded)
    print(encoded, end="")
    return int(bool(not result["validated_proposals"] or result["unsupported_requests"] or result["policy_failures"]
                    or result["malformed_rows"] or result["decode_error_count"] or tail.pending))


if __name__ == "__main__":
    raise SystemExit(main())
