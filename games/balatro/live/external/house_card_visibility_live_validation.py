from __future__ import annotations

import argparse
from pathlib import Path

from games.balatro.live.translator import DefaultBalatroStateTranslator

from .expected_card_locator import locate_card_faces_expected_count
from .hand_mouse import ExternalHandMouseExecutor, HandMouseLayout
from .house_card_visibility import classify_house_card_visibility
from .mouse import BalatroMouseController
from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader


DEFAULT_LAYOUT = "balatro-hand-mouse.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only The House visibility diagnostic. Prints only public screen "
            "visibility metrics and never exposes save-backed card identities."
        )
    )
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--layout", default=DEFAULT_LAYOUT)
    args = parser.parse_args()

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    translator = DefaultBalatroStateTranslator()
    state = translator.translate(observer.observe())

    if state.phase != "SELECTING_HAND":
        parser.error(f"Balatro save is in {state.phase}, expected SELECTING_HAND")
    if state.boss_name != "The House":
        parser.error(f"expected The House, observed {state.boss_name!r}")
    if not state.hand:
        parser.error("save contains no hand cards")

    try:
        layout = HandMouseLayout.load(Path(args.layout))
        mouse = BalatroMouseController(armed=True)
        locator = lambda region: locate_card_faces_expected_count(region, len(state.hand))
        with ExternalHandMouseExecutor(
            layout,
            mouse=mouse,
            card_locator=locator,
        ) as executor:
            frame, locations = executor.locate_hand(state)
            visibility = classify_house_card_visibility(frame, locations)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    face_up = sum(1 for item in visibility if item.face_up)
    print(f"Save -> {reader.path}")
    print(f"Phase -> {state.phase}")
    print(f"Boss -> {state.boss_name}")
    print(f"Discards remaining -> {state.discards_remaining}")
    print(f"Screen/save exact-count guard -> PASS ({len(locations)})")
    print(f"Screen face-up cards -> {face_up}")
    print(f"Screen face-down cards -> {len(visibility) - face_up}")
    for item in visibility:
        label = "FACE UP" if item.face_up else "FACE DOWN"
        print(
            f"  Screen {item.index}: {label} "
            f"neutral_fraction={item.neutral_fraction:.6f} "
            f"mean_brightness={item.mean_brightness:.3f} "
            f"mean_chroma={item.mean_chroma:.3f}"
        )
    print("Hidden save card identities printed -> False")
    print("Mouse input sent -> False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
