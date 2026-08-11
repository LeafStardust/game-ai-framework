from __future__ import annotations

import argparse
from pathlib import Path

from games.balatro.live.synchronizer import BalatroLiveSynchronizer
from games.balatro.live.translator import DefaultBalatroStateTranslator

from .mouse import BalatroMouseController
from .round_eval_mouse import ExternalRoundEvalMouseExecutor, RoundEvalMouseLayout
from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader


DEFAULT_LAYOUT = "balatro-round-eval-mouse.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or execute exactly one calibrated Balatro Cash Out click and "
            "verify the ROUND_EVAL -> SHOP save transition."
        )
    )
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--layout", default=DEFAULT_LAYOUT)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="arm mouse input and click Cash Out exactly once",
    )
    args = parser.parse_args()

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    translator = DefaultBalatroStateTranslator()
    snapshot = observer.observe()
    state = translator.translate(snapshot)

    if state.phase != "ROUND_EVAL":
        parser.error(f"Balatro save is in {state.phase}, expected ROUND_EVAL")

    try:
        layout = RoundEvalMouseLayout.load(Path(args.layout))
        point = layout.point_for("cash-out")
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    print(f"Save -> {reader.path}")
    print(f"Phase before -> {state.phase}")
    print(f"Ante -> {state.ante}")
    print(f"Round -> {state.round}")
    print(f"Score -> {state.score}")
    print(f"Money before -> {state.money}")
    print(f"Control -> Cash Out")
    print(f"Point -> click({point.x:.4f},{point.y:.4f})")

    if not args.execute:
        print("Mouse input sent -> False")
        print("Re-run with --execute to send exactly this one Cash Out click.")
        return 0

    mouse = BalatroMouseController(armed=True)
    try:
        with ExternalRoundEvalMouseExecutor(layout, mouse=mouse) as executor:
            executor.dispatch("cash-out")

        print("Mouse input sent -> True")
        print("Waiting for save checkpoint -> SHOP")
        persisted = BalatroLiveSynchronizer(
            observer,
            poll_interval=0.05,
            timeout=15.0,
        ).wait_for_change(
            snapshot,
            phases={"SHOP"},
            require_complete=False,
        )
        persisted_state = translator.translate(persisted)
    except (RuntimeError, TimeoutError, ValueError) as error:
        parser.error(str(error))

    print(f"Phase after -> {persisted_state.phase}")
    print(f"Ante after -> {persisted_state.ante}")
    print(f"Round after -> {persisted_state.round}")
    print(f"Money after -> {persisted_state.money}")
    print(f"Shop Jokers -> {len(persisted_state.shop_jokers)}")
    print(f"Shop consumables -> {len(persisted_state.shop_consumables)}")
    print(f"Shop boosters -> {len(persisted_state.shop_boosters)}")
    print(f"Shop vouchers -> {len(persisted_state.shop_vouchers)}")
    print("Checkpoint verified -> True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
