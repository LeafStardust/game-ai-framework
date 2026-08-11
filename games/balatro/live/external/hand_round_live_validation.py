from __future__ import annotations

import argparse
from pathlib import Path

from .hand_controller import ExternalHandController
from .hand_mouse import ExternalHandMouseExecutor, HandMouseLayout
from .mouse import BalatroMouseController
from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader


DEFAULT_LAYOUT = "balatro-hand-mouse.json"


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
            "Preview or execute a bounded checkpointed Balatro hand-action loop. "
            "Each action is chosen from a fresh persisted save checkpoint."
        )
    )
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--layout", default=DEFAULT_LAYOUT)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="arm mouse input and execute the checkpointed hand-action loop",
    )
    parser.add_argument(
        "--max-actions",
        type=int,
        default=8,
        help="hard maximum number of hand actions in one process",
    )
    args = parser.parse_args()

    if args.max_actions < 1:
        parser.error("--max-actions must be at least 1")

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    layout_path = Path(args.layout)
    try:
        layout = HandMouseLayout.load(layout_path)
        layout.point_for("play-hand")
        layout.point_for("discard")
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    mouse = BalatroMouseController(armed=args.execute)
    try:
        with ExternalHandMouseExecutor(layout, mouse=mouse) as executor:
            controller = ExternalHandController(observer, executor)
            snapshot, state = controller.observe()

            print(f"Save -> {reader.path}")
            print(f"Phase -> {state.phase}")
            print(f"Score -> {state.score}")
            print(f"Blind target -> {getattr(state.blind, 'requirement', 0)}")
            print(f"Hands -> {state.hands_remaining}")
            print(f"Discards -> {state.discards_remaining}")

            if state.phase != "SELECTING_HAND":
                print("Hand loop ready -> False")
                print(f"Reason -> current phase is {state.phase}")
                print("Mouse input sent -> False")
                return 0

            recommendation = controller.recommend(state)
            indices = executor.card_indices(state, recommendation)
            _, locations = executor.locate_hand(state)
            print(f"Next recommendation -> {recommendation.name}")
            print("Selected indices -> " + ",".join(str(index) for index in indices))
            for index in indices:
                location = locations[index]
                print(
                    f"  {index}: {_card_text(state.hand[index])} "
                    f"-> center=({location.center.x:.4f},{location.center.y:.4f})"
                )

            if not args.execute:
                print("Hand loop ready -> True")
                print("Mouse input sent -> False")
                print("Re-run with --execute to run the bounded checkpointed loop.")
                return 0

            print(f"Action cap -> {args.max_actions}")
            result = controller.execute_until_phase_change(max_actions=args.max_actions)
    except (RuntimeError, TimeoutError, ValueError) as error:
        parser.error(str(error))

    print("Mouse input sent -> True")
    for number, step in enumerate(result.steps, start=1):
        before = step.before_state
        after = step.after_state
        print(
            f"Step {number} -> {step.action.name} "
            f"indices={','.join(str(index) for index in step.indices)} "
            f"score={before.score}->{after.score} "
            f"hands={before.hands_remaining}->{after.hands_remaining} "
            f"discards={before.discards_remaining}->{after.discards_remaining} "
            f"phase={before.phase}->{after.phase}"
        )

    final_state = result.final_state
    if final_state is not None:
        print(f"Final phase -> {final_state.phase}")
        print(f"Final score -> {final_state.score}")
        print(f"Final hands -> {final_state.hands_remaining}")
        print(f"Final discards -> {final_state.discards_remaining}")
        print(f"Final hand cards -> {len(final_state.hand)}")
    print(f"Stop reason -> {result.stop_reason}")
    print("Checkpoint loop verified -> True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
