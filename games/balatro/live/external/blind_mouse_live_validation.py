from __future__ import annotations

import argparse
from pathlib import Path

from games.balatro.live.synchronizer import BalatroLiveSynchronizer
from games.balatro.live.translator import DefaultBalatroStateTranslator

from .blind_mouse import BLIND_CONTROLS, BlindMouseLayout, ExternalBlindMouseExecutor
from .mouse import BalatroMouseController
from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader


DEFAULT_LAYOUT = "balatro-blind-mouse.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or execute exactly one calibrated Balatro blind Select/Skip click."
        )
    )
    parser.add_argument("control", choices=sorted(BLIND_CONTROLS))
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--layout", default=DEFAULT_LAYOUT)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="arm mouse input and click exactly this one blind control",
    )
    args = parser.parse_args()

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    translator = DefaultBalatroStateTranslator()
    snapshot = observer.observe()
    state = translator.translate(snapshot)

    if state.phase != "BLIND_SELECT":
        parser.error(f"Balatro save is in {state.phase}, expected BLIND_SELECT")

    layout_path = Path(args.layout)
    try:
        layout = BlindMouseLayout.load(layout_path)
        point = layout.point_for(args.control)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    blind, operation = args.control.split("-", 1)
    print(f"Save -> {reader.path}")
    print(f"Phase before -> {state.phase}")
    print(f"Ante -> {state.ante}")
    print(f"Round -> {state.round}")
    print(f"Control -> {blind.upper()} Blind {operation.title()}")
    print(f"Point -> click({point.x:.4f},{point.y:.4f})")

    if not args.execute:
        print("Mouse input sent -> False")
        print("Re-run with --execute to send exactly this one blind control click.")
        return 0

    mouse = BalatroMouseController(armed=True)
    try:
        with ExternalBlindMouseExecutor(layout, mouse=mouse) as executor:
            executor.dispatch(args.control)

        print("Mouse input sent -> True")
        expected_phases = {"SELECTING_HAND"} if operation == "select" else {"BLIND_SELECT"}
        expected_text = "SELECTING_HAND" if operation == "select" else "changed BLIND_SELECT"
        print(f"Waiting for save checkpoint -> {expected_text}")
        persisted = BalatroLiveSynchronizer(
            observer,
            poll_interval=0.05,
            timeout=15.0,
        ).wait_for_change(
            snapshot,
            phases=expected_phases,
            require_complete=False,
        )
        persisted_state = translator.translate(persisted)
    except (RuntimeError, TimeoutError, ValueError) as error:
        parser.error(str(error))

    print(f"Phase after -> {persisted_state.phase}")
    print(f"Ante after -> {persisted_state.ante}")
    print(f"Round after -> {persisted_state.round}")
    if operation == "select":
        print(f"Hands -> {persisted_state.hands_remaining}")
        print(f"Discards -> {persisted_state.discards_remaining}")
        print(f"Hand cards -> {len(persisted_state.hand)}")
    print("Checkpoint verified -> True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
