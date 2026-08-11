from __future__ import annotations

import argparse
import time

from games.balatro.live.external.capture import BalatroScreenCapture
from games.balatro.live.external.card_capture import DEFAULT_HAND_REGION
from games.balatro.live.external.expected_card_locator import (
    locate_card_faces_expected_count,
)
from games.balatro.live.external.hand_mouse import ExternalHandMouseExecutor
from games.balatro.live.external.save_observer import SaveBalatroObserver
from games.balatro.live.external.save_state import BalatroSaveReader
from games.balatro.live.external.viewport import BalatroViewport
from games.balatro.live.head_blind_planner import HeadScorer
from games.balatro.live.translator import DefaultBalatroStateTranslator


def _card_text(card) -> str:
    parts = [str(card.rank), str(card.suit)]
    if getattr(card, "enhancement", None):
        parts.append(str(card.enhancement))
    if getattr(card, "edition", None):
        parts.append(str(card.edition))
    if getattr(card, "seal", None):
        parts.append(str(card.seal))
    return " / ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only validation of expected-count hand-grid reconstruction for "
            "The Head. Captures Balatro without focusing or sending mouse input."
        )
    )
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--prepare-delay", type=float, default=3.0)
    args = parser.parse_args()

    if args.prepare_delay < 0:
        parser.error("--prepare-delay cannot be negative")

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    state = DefaultBalatroStateTranslator().translate(observer.observe())

    print(f"Save -> {reader.path}")
    print(f"Phase -> {state.phase}")
    print(f"Boss -> {state.boss_name or 'none'}")
    print(f"Save hand cards -> {len(state.hand)}")

    if state.phase != "SELECTING_HAND":
        parser.error(f"expected SELECTING_HAND, observed {state.phase}")
    if state.boss_name != "The Head":
        parser.error(f"expected The Head, observed {state.boss_name!r}")

    expected_count = len(state.hand)

    if args.prepare_delay > 0:
        print(
            f"Capture starts in {args.prepare_delay:g}s; bring Balatro to the foreground.",
            flush=True,
        )
        time.sleep(args.prepare_delay)

    try:
        with BalatroScreenCapture() as capture:
            frame = capture.capture()
        region = BalatroViewport(frame).crop(DEFAULT_HAND_REGION)
        locations = locate_card_faces_expected_count(region, expected_count)
        if len(locations) != expected_count:
            raise RuntimeError(
                "visible hand/card-save count mismatch: "
                f"screen={len(locations)}, save={expected_count}"
            )
        ExternalHandMouseExecutor._require_unselected_row(locations)
    except (RuntimeError, ValueError) as error:
        parser.error(str(error))

    scorer = HeadScorer()
    print(f"Screen hand cards -> {len(locations)}")
    print("Resting-row guard -> PASS")
    for index, (card, location) in enumerate(zip(state.hand, locations)):
        suffix = " [DEBUFFED]" if scorer.is_card_debuffed(card) else ""
        print(
            f"  {index}: {_card_text(card)}{suffix} "
            f"-> center=({location.center.x:.4f},{location.center.y:.4f})"
        )
    print("Card/save exact-count guard -> PASS")
    print("Mouse input sent -> False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
