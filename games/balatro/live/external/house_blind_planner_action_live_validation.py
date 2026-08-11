from __future__ import annotations

import argparse
from pathlib import Path

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.live.blind_clear_planner import PlannerSearchBudgetExceeded
from games.balatro.live.depth_draw_outcomes import DepthAwarePublicDrawOutcomeModel
from games.balatro.live.house_blind_planner import HouseBlindClearPlanner
from games.balatro.live.synchronizer import BalatroLiveSynchronizer
from games.balatro.live.translator import DefaultBalatroStateTranslator

from .blind_clear_planner_action_live_validation import (
    PROBABILITY_TOLERANCE,
    _card_text,
    _indices,
    _is_guaranteed,
    _joker_text,
    _parse_indices,
)
from .expected_card_locator import locate_card_faces_expected_count
from .hand_mouse import ExternalHandMouseExecutor, HandMouseLayout
from .house_card_visibility import classify_house_card_visibility
from .mouse import BalatroMouseController
from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader


DEFAULT_LAYOUT = "balatro-hand-mouse.json"
MAX_DISCARD_CARDS = 5


def _planner(args) -> HouseBlindClearPlanner:
    child_samples = args.child_samples
    if child_samples is None:
        child_samples = max(1, args.samples // 2) if args.horizon > 2 else args.samples

    max_nodes = args.max_nodes
    if max_nodes is None and args.horizon > 2:
        max_nodes = 1000

    return HouseBlindClearPlanner(
        draw_outcomes=DepthAwarePublicDrawOutcomeModel(
            exact_combination_limit=args.exact_limit,
            root_sample_count=args.samples,
            child_sample_count=child_samples,
            child_exact_combination_limit=args.child_exact_limit,
        ),
        play_width=args.play_width,
        discard_width=args.discard_width,
        child_play_width=args.child_play_width,
        child_discard_width=args.child_discard_width,
        horizon=args.horizon,
        max_nodes=max_nodes,
    )


def _visibility_indices(visibility, *, face_up: bool) -> tuple[int, ...]:
    return tuple(item.index for item in visibility if item.face_up is face_up)


def _print_visibility(visibility) -> tuple[int, ...]:
    face_down = _visibility_indices(visibility, face_up=False)
    print(f"Screen face-up cards -> {len(visibility) - len(face_down)}")
    print(f"Screen face-down cards -> {len(face_down)}")
    for item in visibility:
        label = "FACE UP" if item.face_up else "FACE DOWN"
        print(f"  Screen {item.index}: {label}")
    return face_down


def _print_plan(prefix: str, state, plan) -> tuple[int, ...]:
    indices = _indices(state, plan.action)
    print(f"{prefix} -> {plan.action.name}")
    print(f"{prefix} indices -> " + ",".join(str(index) for index in indices))
    for index in indices:
        print(f"  {index}: {_card_text(state.hand[index])}")
    print(f"{prefix} clear probability -> {plan.value.clear_probability:.6f}")
    print(f"{prefix} expected score -> {plan.value.expected_score:.3f}")
    print(f"{prefix} exact -> {plan.exact}")
    print(f"{prefix} guaranteed clear -> {_is_guaranteed(plan)}")
    return indices


def _load_layout(path: str) -> HandMouseLayout:
    layout = HandMouseLayout.load(Path(path))
    layout.point_for("play-hand")
    layout.point_for("discard")
    return layout


def _locator(expected_count: int):
    return lambda region: locate_card_faces_expected_count(region, expected_count)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or execute exactly one guarded The House action. Face-down "
            "positions are detected from screen pixels and discarded without using "
            "their hidden save identities for decision-making. Once every held card "
            "is visibly face-up, normal public-state blind-clear planning resumes."
        )
    )
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--layout", default=DEFAULT_LAYOUT)
    parser.add_argument("--play-width", type=int, default=4)
    parser.add_argument("--discard-width", type=int, default=2)
    parser.add_argument("--child-play-width", type=int, default=2)
    parser.add_argument("--child-discard-width", type=int, default=1)
    parser.add_argument("--horizon", type=int, default=3)
    parser.add_argument("--max-nodes", type=int, default=2000)
    parser.add_argument("--samples", type=int, default=16)
    parser.add_argument("--child-samples", type=int, default=1)
    parser.add_argument(
        "--exact-limit",
        type=int,
        default=HouseBlindClearPlanner.DEFAULT_EXACT_DRAW_COMBINATION_LIMIT,
    )
    parser.add_argument("--child-exact-limit", type=int)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--expect-action", choices=[PLAY_CARDS, DISCARD_CARDS])
    parser.add_argument("--expect-indices")
    parser.add_argument("--allow-probabilistic", action="store_true")
    parser.add_argument("--min-clear-probability", type=float)
    parser.add_argument("--expect-clear-probability", type=float)
    args = parser.parse_args()

    if args.horizon < 1:
        parser.error("--horizon must be at least 1")
    if args.play_width < 1 or args.child_play_width < 1:
        parser.error("play widths must be positive")
    if args.discard_width < 0 or args.child_discard_width < 0:
        parser.error("discard widths cannot be negative")
    if args.max_nodes is not None and args.max_nodes < 1:
        parser.error("--max-nodes must be positive")
    if args.samples < 1 or args.child_samples < 1:
        parser.error("sample counts must be positive")
    if args.exact_limit < 1:
        parser.error("--exact-limit must be positive")
    if args.child_exact_limit is not None and args.child_exact_limit < 1:
        parser.error("--child-exact-limit must be positive")
    if args.execute and (args.expect_action is None or args.expect_indices is None):
        parser.error("--execute requires --expect-action and --expect-indices")
    if not args.execute and (args.expect_action is not None or args.expect_indices is not None):
        parser.error("--expect-action/--expect-indices are only valid with --execute")
    if args.allow_probabilistic:
        if args.min_clear_probability is None:
            parser.error("--allow-probabilistic requires --min-clear-probability")
        if not 0.0 <= args.min_clear_probability <= 1.0:
            parser.error("--min-clear-probability must be between 0 and 1")
        if args.execute and args.expect_clear_probability is None:
            parser.error("probabilistic --execute requires --expect-clear-probability")
    elif args.min_clear_probability is not None or args.expect_clear_probability is not None:
        parser.error(
            "--min-clear-probability/--expect-clear-probability require --allow-probabilistic"
        )

    try:
        expected_indices = (
            _parse_indices(args.expect_indices) if args.expect_indices is not None else None
        )
    except ValueError as error:
        parser.error(str(error))

    try:
        layout = _load_layout(args.layout)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    translator = DefaultBalatroStateTranslator()
    snapshot = observer.observe()
    state = translator.translate(snapshot)

    if state.phase != "SELECTING_HAND":
        parser.error(f"Balatro save is in {state.phase}, expected SELECTING_HAND")
    if not state.hand:
        parser.error("save contains no hand cards")
    if state.boss_name != HouseBlindClearPlanner.BOSS_NAME:
        parser.error(
            f"expected {HouseBlindClearPlanner.BOSS_NAME}, observed {state.boss_name!r}"
        )

    planner = _planner(args)
    unsupported = planner.evaluator.score_outcomes.joker_projector.unsupported_jokers(state)
    if unsupported:
        parser.error(
            "House execution is blocked by unsupported Joker projection(s): "
            + ", ".join(unsupported)
        )

    mouse = BalatroMouseController(armed=True)
    try:
        with ExternalHandMouseExecutor(
            layout,
            mouse=mouse,
            card_locator=_locator(len(state.hand)),
        ) as executor:
            frame, locations = executor.locate_hand(state)
            visibility = classify_house_card_visibility(frame, locations)

            print(f"Save -> {reader.path}")
            print(f"Phase before -> {state.phase}")
            print(f"Boss -> {state.boss_name}")
            print("Boss modifier support -> True")
            print("Boss rule -> first hand is drawn face down")
            print(f"Score before -> {state.score}")
            print(f"Blind target -> {getattr(state.blind, 'requirement', 0)}")
            print(f"Hands before -> {state.hands_remaining}")
            print(f"Discards before -> {state.discards_remaining}")
            print(f"Screen/save exact-count guard -> PASS ({len(locations)})")
            face_down = _print_visibility(visibility)

            if face_down:
                if int(getattr(state, "discards_remaining", 0)) <= 0:
                    print("Execution guard -> BLOCKED")
                    print("Reason -> face-down cards remain but no discards are available")
                    print("Mouse input sent -> False")
                    return 0

                recommended_indices = face_down[:MAX_DISCARD_CARDS]
                print("Visibility-clearing action -> DISCARD_CARDS")
                print(
                    "Recommended indices -> "
                    + ",".join(str(index) for index in recommended_indices)
                )
                for index in recommended_indices:
                    print(f"  {index}: [FACE DOWN; identity intentionally withheld]")
                print("Hidden save card identities used for choice -> False")
                print("Execution mode -> public-visibility discard")
                print("Execution guard -> PASS")

                if not args.execute:
                    print("Mouse input sent -> False")
                    print(
                        "Re-run with --execute --expect-action DISCARD_CARDS and the "
                        "exact indices above to send one guarded visibility-clearing action."
                    )
                    return 0

                if args.expect_action != DISCARD_CARDS:
                    parser.error(
                        "House visibility recommendation changed before execution: "
                        f"expected action={args.expect_action}, observed={DISCARD_CARDS}"
                    )
                if expected_indices != recommended_indices:
                    parser.error(
                        "House face-down positions changed before execution: "
                        f"expected indices={expected_indices}, observed={recommended_indices}"
                    )

                action = BalatroAction(
                    DISCARD_CARDS,
                    [state.hand[index] for index in recommended_indices],
                )
                executed = executor.dispatch_with_locations(
                    action,
                    state,
                    frame,
                    locations,
                )
                if executed != recommended_indices:
                    raise RuntimeError(
                        "House executor index mapping changed during dispatch"
                    )
            else:
                print("Public visibility gate -> PASS (all held cards face-up)")
                try:
                    plan = planner.plan(state)
                except PlannerSearchBudgetExceeded as error:
                    print("Execution guard -> BLOCKED")
                    print(f"Reason -> {error}")
                    print(f"Planner nodes evaluated -> {planner.nodes_evaluated}")
                    print("Mouse input sent -> False")
                    return 0

                print(f"Planner horizon -> {args.horizon} actions")
                print(f"Planner nodes evaluated -> {planner.nodes_evaluated}")
                print(f"Owned Jokers -> {len(state.jokers)}")
                for index, joker in enumerate(state.jokers):
                    print(f"  J{index}: {_joker_text(joker)}")
                print("Joker projection complete -> True")
                print("Hidden draw order used -> False")
                indices = _print_plan("Recommended", state, plan)
                guaranteed = _is_guaranteed(plan)
                probabilistic = (
                    args.allow_probabilistic
                    and args.min_clear_probability is not None
                    and plan.value.clear_probability + PROBABILITY_TOLERANCE
                    >= args.min_clear_probability
                )
                guard_passes = guaranteed or probabilistic
                if guaranteed:
                    print("Execution mode -> exact-guaranteed")
                elif args.allow_probabilistic:
                    print(
                        "Execution mode -> probabilistic "
                        f"(minimum={args.min_clear_probability:.6f})"
                    )
                else:
                    print("Execution mode -> exact-guaranteed")
                print(f"Execution guard -> {'PASS' if guard_passes else 'BLOCKED'}")
                if not guard_passes:
                    print("Reason -> recommendation is not allowed by selected execution mode")
                    print("Mouse input sent -> False")
                    return 0
                if not args.execute:
                    print("Mouse input sent -> False")
                    return 0
                if plan.action.name != args.expect_action:
                    parser.error(
                        "planner recommendation changed before execution: "
                        f"expected action={args.expect_action}, observed={plan.action.name}"
                    )
                if indices != expected_indices:
                    parser.error(
                        "planner cards changed before execution: "
                        f"expected indices={expected_indices}, observed={indices}"
                    )
                if not guaranteed and args.allow_probabilistic:
                    assert args.expect_clear_probability is not None
                    if (
                        abs(plan.value.clear_probability - args.expect_clear_probability)
                        > PROBABILITY_TOLERANCE
                    ):
                        parser.error(
                            "planner clear probability changed before execution: "
                            f"expected={args.expect_clear_probability:.6f}, "
                            f"observed={plan.value.clear_probability:.6f}"
                        )
                executed = executor.dispatch_with_locations(
                    plan.action,
                    state,
                    frame,
                    locations,
                )
                if executed != indices:
                    raise RuntimeError("House executor index mapping changed during dispatch")
    except (RuntimeError, TimeoutError, ValueError) as error:
        parser.error(str(error))

    print("Mouse input sent -> True")
    print("Waiting for save checkpoint -> changed hand/round state")
    try:
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
    print(f"Owned Jokers after -> {len(persisted_state.jokers)}")
    for index, joker in enumerate(persisted_state.jokers):
        print(f"  J{index}: {_joker_text(joker)}")
    print("Checkpoint verified -> True")
    print("Replan deferred -> re-run House validator for a fresh public-visibility capture")
    print("Follow-up mouse input sent -> False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
