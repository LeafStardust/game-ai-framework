from __future__ import annotations

import argparse
from pathlib import Path

from framework.agent.agent import Agent
from framework.decision.pipeline import DecisionPipeline
from framework.decision.policies.greedy import GreedyPolicy

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.card_selector import CardSelector
from games.balatro.evaluator import BalatroEvaluator
from games.balatro.live.synchronizer import BalatroLiveSynchronizer
from games.balatro.live.translator import DefaultBalatroStateTranslator

from .hand_mouse import ExternalHandMouseExecutor, HandMouseLayout
from .mouse import BalatroMouseController
from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader


DEFAULT_LAYOUT = "balatro-hand-mouse.json"


def _agent() -> Agent:
    return Agent(
        DecisionPipeline(
            BalatroEvaluator(),
            GreedyPolicy(),
        )
    )


def _indices_text(indices: tuple[int, ...]) -> str:
    return ",".join(str(index) for index in indices)


def _parse_indices(value: str) -> tuple[int, ...]:
    try:
        indices = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    except ValueError as error:
        raise ValueError("--expect-indices must be comma-separated integers") from error
    if not indices:
        raise ValueError("--expect-indices cannot be empty")
    if any(index < 0 for index in indices):
        raise ValueError("--expect-indices cannot contain negative indexes")
    return indices


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
            "Preview or execute exactly one greedy Balatro PLAY_CARDS/DISCARD_CARDS "
            "decision using save-state cards and dynamically located screen positions."
        )
    )
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--layout", default=DEFAULT_LAYOUT)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="arm normal mouse input and execute exactly the current recommendation",
    )
    parser.add_argument(
        "--expect-action",
        choices=[PLAY_CARDS, DISCARD_CARDS],
        help="required with --execute; exact recommended action expected",
    )
    parser.add_argument(
        "--expect-indices",
        help="required with --execute; exact comma-separated save/screen card indexes expected",
    )
    args = parser.parse_args()

    if args.execute and (args.expect_action is None or args.expect_indices is None):
        parser.error("--execute requires --expect-action and --expect-indices")
    if not args.execute and (args.expect_action is not None or args.expect_indices is not None):
        parser.error("--expect-action/--expect-indices are only valid with --execute")

    try:
        expected_indices = (
            _parse_indices(args.expect_indices) if args.expect_indices is not None else None
        )
    except ValueError as error:
        parser.error(str(error))

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    translator = DefaultBalatroStateTranslator()
    snapshot = observer.observe()
    state = translator.translate(snapshot)

    if state.phase != "SELECTING_HAND":
        parser.error(f"Balatro save is in {state.phase}, expected SELECTING_HAND")
    if not state.hand:
        parser.error("save contains no playable hand cards")

    actions = CardSelector().generate_actions(state)
    if not actions:
        parser.error("no legal play/discard actions were generated")
    recommendation = _agent().act(state, actions)

    layout_path = Path(args.layout)
    try:
        layout = HandMouseLayout.load(layout_path)
        layout.point_for("play-hand")
        layout.point_for("discard")
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    mouse = BalatroMouseController(armed=True)
    try:
        with ExternalHandMouseExecutor(layout, mouse=mouse) as executor:
            indices = executor.card_indices(state, recommendation)
            _, locations = executor.locate_hand(state)

            print(f"Save -> {reader.path}")
            print(f"Phase before -> {state.phase}")
            print(f"Score before -> {state.score}")
            print(f"Blind target -> {getattr(state.blind, 'requirement', 0)}")
            print(f"Hands before -> {state.hands_remaining}")
            print(f"Discards before -> {state.discards_remaining}")
            print(f"Recommended -> {recommendation.name}")
            print(f"Selected indices -> {_indices_text(indices)}")
            for index in indices:
                location = locations[index]
                print(
                    f"  {index}: {_card_text(state.hand[index])} "
                    f"-> center=({location.center.x:.4f},{location.center.y:.4f})"
                )

            if not args.execute:
                print("Mouse input sent -> False")
                print(
                    "Re-run with --execute plus the exact action and indices above "
                    "to send one guarded hand action."
                )
                return 0

            if recommendation.name != args.expect_action:
                parser.error(
                    "recommendation changed before execution: "
                    f"expected action={args.expect_action}, observed={recommendation.name}"
                )
            if indices != expected_indices:
                parser.error(
                    "recommended cards changed before execution: "
                    f"expected indices={expected_indices}, observed={indices}"
                )

            executed_indices = executor.dispatch(recommendation, state)
            if executed_indices != indices:
                raise RuntimeError("hand executor index mapping changed during dispatch")

        print("Mouse input sent -> True")
        print("Waiting for save checkpoint -> changed hand/round state")
        persisted = BalatroLiveSynchronizer(
            observer,
            poll_interval=0.05,
            timeout=20.0,
        ).wait_for_change(
            snapshot,
            phases={"SELECTING_HAND", "ROUND_EVAL"},
            require_complete=False,
        )
        persisted_state = translator.translate(persisted)
    except (RuntimeError, TimeoutError, ValueError) as error:
        parser.error(str(error))

    print(f"Phase after -> {persisted_state.phase}")
    print(f"Score after -> {persisted_state.score}")
    print(f"Hands after -> {persisted_state.hands_remaining}")
    print(f"Discards after -> {persisted_state.discards_remaining}")
    print(f"Hand cards after -> {len(persisted_state.hand)}")
    print("Checkpoint verified -> True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
