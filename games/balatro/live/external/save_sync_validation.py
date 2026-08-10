from __future__ import annotations

import argparse
import time

from games.balatro.live.synchronizer import BalatroLiveSynchronizer
from games.balatro.live.translator import DefaultBalatroStateTranslator

from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader


def state_summary(snapshot) -> dict:
    state = DefaultBalatroStateTranslator().translate(snapshot)
    blind = snapshot.payload.get("blind") or {}
    return {
        "sequence": snapshot.sequence,
        "phase": state.phase,
        "save_state": snapshot.payload.get("save_state"),
        "hash": str(snapshot.payload.get("save_sha256", ""))[:12],
        "ante": state.ante,
        "round": state.round,
        "money": state.money,
        "score": state.score,
        "blind": blind.get("name"),
        "blind_target": state.blind_score,
        "hands": state.hands_remaining,
        "discards": state.discards_remaining,
        "hand": [f"{card.rank} {card.suit}" for card in state.hand],
    }


def changed_fields(before: dict, after: dict) -> list[str]:
    fields = []
    for key in before:
        if key in {"sequence", "hash"}:
            continue
        if before[key] != after.get(key):
            fields.append(key)
    return fields


def _print_summary(label: str, summary: dict) -> None:
    hand = ", ".join(summary["hand"]) or "none"
    print(
        f"{label}: sequence={summary['sequence']} hash={summary['hash']} "
        f"phase={summary['phase']} save_state={summary['save_state']}"
    )
    print(
        f"  ante={summary['ante']} round={summary['round']} money={summary['money']} "
        f"score={summary['score']} blind={summary['blind']} "
        f"target={summary['blind_target']} hands={summary['hands']} "
        f"discards={summary['discards']}"
    )
    print(f"  hand[{len(summary['hand'])}] -> {hand}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure how quickly vanilla Balatro save.jkr publishes a gameplay change."
    )
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--poll-interval", type=float, default=0.05)
    args = parser.parse_args()

    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.poll_interval < 0:
        parser.error("--poll-interval cannot be negative")

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    synchronizer = BalatroLiveSynchronizer(
        observer,
        poll_interval=args.poll_interval,
        timeout=args.timeout,
    )

    before_snapshot = observer.observe()
    before = state_summary(before_snapshot)
    print(f"Save -> {reader.path}")
    _print_summary("Before", before)
    print(
        f"Waiting up to {args.timeout:g}s for the next save update. "
        "Perform one normal Balatro action now.",
        flush=True,
    )

    started = time.monotonic()
    try:
        after_snapshot = synchronizer.wait_for_change(
            before_snapshot,
            require_complete=False,
        )
    except TimeoutError as error:
        parser.error(str(error))
    elapsed = time.monotonic() - started

    after = state_summary(after_snapshot)
    _print_summary("After", after)
    changes = changed_fields(before, after)
    print(f"Save update latency -> {elapsed:.3f}s")
    print("Changed fields -> " + (", ".join(changes) if changes else "metadata only"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
