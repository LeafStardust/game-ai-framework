from __future__ import annotations

import argparse
import time

from games.balatro.live.translator import DefaultBalatroStateTranslator

from .capture import BalatroScreenCapture
from .card_capture import DEFAULT_HAND_REGION
from .card_locator import locate_card_faces
from .mouse import BalatroMouseController
from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader
from .viewport import BalatroViewport


def _capture_focused(
    capture: BalatroScreenCapture,
    mouse: BalatroMouseController,
    *,
    timeout: float = 1.5,
    poll_interval: float = 0.02,
    settle_delay: float = 0.25,
):
    tracker = capture.tracker
    window = tracker.snapshot()
    mouse.focus(window)

    locator = getattr(tracker, "locator", None)
    foreground_handle = getattr(locator, "foreground_handle", None)
    if callable(foreground_handle):
        deadline = time.monotonic() + max(0.0, timeout)
        while foreground_handle() != window.handle:
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    "Balatro did not become the foreground window before hand capture"
                )
            if poll_interval > 0:
                time.sleep(poll_interval)

    if settle_delay > 0:
        time.sleep(settle_delay)
    return capture.capture()


def _card_label(card) -> str:
    parts = [str(card.rank), str(card.suit)]
    if card.enhancement:
        parts.append(str(card.enhancement))
    if card.edition:
        parts.append(str(card.edition))
    if card.seal:
        parts.append(f"{card.seal} Seal")
    return " / ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate that save.jkr hand order maps to left-to-right live card positions. "
            "This command never clicks a card."
        )
    )
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--sample-step", type=int, default=2)
    parser.add_argument("--min-brightness", type=int, default=165)
    parser.add_argument("--max-channel-spread", type=int, default=70)
    args = parser.parse_args()

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    translator = DefaultBalatroStateTranslator()
    snapshot = observer.observe()
    state = translator.translate(snapshot)

    if state.phase != "SELECTING_HAND":
        parser.error(f"Balatro save is in {state.phase}, expected SELECTING_HAND")
    if not state.hand:
        parser.error("save contains no visible hand cards")

    mouse = BalatroMouseController(armed=True)
    try:
        with BalatroScreenCapture() as capture:
            frame = _capture_focused(capture, mouse)
            hand_region = BalatroViewport(frame).crop(DEFAULT_HAND_REGION)
            locations = locate_card_faces(
                hand_region,
                sample_step=args.sample_step,
                min_brightness=args.min_brightness,
                max_channel_spread=args.max_channel_spread,
            )
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    print(f"Save -> {reader.path}")
    print(f"Phase -> {state.phase}")
    print(f"Save hand cards -> {len(state.hand)}")
    print(f"Detected screen cards -> {len(locations)}")

    if len(locations) != len(state.hand):
        print("Order mapping ready -> False")
        print("Mouse input sent -> False")
        parser.error(
            "screen card count does not match save hand count; do not use index mapping"
        )

    print("Assumed mapping: save order == left-to-right screen order")
    for index, (card, location) in enumerate(zip(state.hand, locations)):
        print(
            f"{index}: {_card_label(card)} "
            f"live_id={card.live_id} -> center=({location.center.x:.4f},{location.center.y:.4f})"
        )

    print("Order mapping ready -> requires visual confirmation")
    print("Mouse input sent -> False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
