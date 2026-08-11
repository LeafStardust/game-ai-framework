from __future__ import annotations

import argparse
from pathlib import Path

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.draw_outcomes import PublicDrawOutcomeModel
from games.balatro.live.synchronizer import BalatroLiveSynchronizer
from games.balatro.live.translator import DefaultBalatroStateTranslator

from .hand_mouse import ExternalHandMouseExecutor, HandMouseLayout
from .mouse import BalatroMouseController
from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader


DEFAULT_LAYOUT = "balatro-hand-mouse.json"
PROBABILITY_TOLERANCE = 1e-9


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


def _indices(state, action) -> tuple[int, ...]:
    selected_ids = {id(card) for card in action.cards}
    return tuple(
        index
        for index, card in enumerate(state.hand)
        if id(card) in selected_ids
    )


def _card_text(card) -> str:
    parts = [str(card.rank), str(card.suit)]
    if getattr(card, "enhancement", None):
        parts.append(str(card.enhancement))
    if getattr(card, "edition", None):
        parts.append(str(card.edition))
    if getattr(card, "seal", None):
        parts.append(str(card.seal))
    return " / ".join(parts)


def _joker_text(joker) -> str:
    label = getattr(joker, "label", None) or type(joker).__name__
    fields = []
    for field in ("chips", "chip_mod"):
        value = getattr(joker, field, None)
        if value is not None:
            fields.append(f"{field}={value}")
    return str(label) + (f" ({', '.join(fields)})" if fields else "")


def _planner(args) -> LiveBlindClearPlanner:
    return LiveBlindClearPlanner(
        draw_outcomes=PublicDrawOutcomeModel(
            exact_combination_limit=args.exact_limit,
            sample_count=args.samples,
        ),
        play_width=args.play_width,
        discard_width=args.discard_width,
        horizon=args.horizon,
    )


def _is_guaranteed(plan) -> bool:
    return plan.exact and plan.value.clear_probability >= 1.0 - 1e-12


def _probabilistic_guard_passes(plan, minimum: float | None) -> bool:
    if minimum is None:
        return False
    return plan.value.clear_probability + PROBABILITY_TOLERANCE >= minimum


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or execute exactly one guarded public-state blind-clear planner "
            "action, wait for the authoritative save checkpoint, then replan without "
            "automatically executing the follow-up action."
        )
    )
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--layout", default=DEFAULT_LAYOUT)
    parser.add_argument("--play-width", type=int, default=6)
    parser.add_argument("--discard-width", type=int, default=4)
    parser.add_argument("--horizon", type=int, default=2)
    parser.add_argument(
        "--samples",
        type=int,
        default=LiveBlindClearPlanner.DEFAULT_DRAW_SAMPLE_COUNT,
    )
    parser.add_argument(
        "--exact-limit",
        type=int,
        default=LiveBlindClearPlanner.DEFAULT_EXACT_DRAW_COMBINATION_LIMIT,
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="execute exactly one recommendation if every safety gate passes",
    )
    parser.add_argument(
        "--expect-action",
        choices=[PLAY_CARDS, DISCARD_CARDS],
        help="required with --execute; exact planner action expected",
    )
    parser.add_argument(
        "--expect-indices",
        help="required with --execute; exact comma-separated current hand indexes expected",
    )
    parser.add_argument(
        "--allow-probabilistic",
        action="store_true",
        help=(
            "allow a sampled/inexact recommendation only when its reported clear "
            "probability also satisfies an explicit threshold"
        ),
    )
    parser.add_argument(
        "--min-clear-probability",
        type=float,
        help="required with --allow-probabilistic; minimum accepted clear probability",
    )
    parser.add_argument(
        "--expect-clear-probability",
        type=float,
        help=(
            "required with probabilistic --execute; exact clear probability printed "
            "by the preceding dry run"
        ),
    )
    args = parser.parse_args()

    if args.horizon < 1:
        parser.error("--horizon must be at least 1")
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
            parser.error(
                "probabilistic --execute requires --expect-clear-probability"
            )
    elif args.min_clear_probability is not None or args.expect_clear_probability is not None:
        parser.error(
            "--min-clear-probability/--expect-clear-probability require "
            "--allow-probabilistic"
        )
    if args.expect_clear_probability is not None and not 0.0 <= args.expect_clear_probability <= 1.0:
        parser.error("--expect-clear-probability must be between 0 and 1")

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
        parser.error("save contains no visible hand cards")
    if state.boss_name:
        parser.error(
            "planner execution is blocked until boss-blind modifier integration is "
            f"validated for {state.boss_name}"
        )

    planner = _planner(args)
    unsupported = planner.evaluator.score_outcomes.joker_projector.unsupported_jokers(state)
    if unsupported:
        parser.error(
            "planner execution is blocked by unsupported Joker projection(s): "
            + ", ".join(unsupported)
        )

    try:
        plan = planner.plan(state)
    except (RuntimeError, ValueError) as error:
        parser.error(str(error))

    print(f"Save -> {reader.path}")
    print(f"Phase before -> {state.phase}")
    print(f"Score before -> {state.score}")
    print(f"Blind target -> {getattr(state.blind, 'requirement', 0)}")
    print(f"Hands before -> {state.hands_remaining}")
    print(f"Discards before -> {state.discards_remaining}")
    print(f"Planner horizon -> {args.horizon} actions")
    print(f"Owned Jokers -> {len(state.jokers)}")
    for index, joker in enumerate(state.jokers):
        print(f"  J{index}: {_joker_text(joker)}")
    print("Joker projection complete -> True")
    print("Hidden draw order used -> False")
    indices = _print_plan("Recommended", state, plan)

    guaranteed = _is_guaranteed(plan)
    probabilistic = args.allow_probabilistic and _probabilistic_guard_passes(
        plan,
        args.min_clear_probability,
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
        if args.allow_probabilistic:
            print(
                "Reason -> recommendation clear probability is below the explicit "
                "probabilistic threshold"
            )
        else:
            print("Reason -> recommendation is not an exact guaranteed-clear continuation")
        print("Mouse input sent -> False")
        return 0

    if not args.execute:
        print("Mouse input sent -> False")
        if guaranteed:
            print(
                "Re-run with --execute plus the exact action and indices above to send "
                "one guarded planner action."
            )
        else:
            print(
                "Re-run with --execute, the exact action/indices/clear probability "
                "above, and the same probabilistic threshold to send one guarded "
                "planner action."
            )
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
        if abs(plan.value.clear_probability - args.expect_clear_probability) > PROBABILITY_TOLERANCE:
            parser.error(
                "planner clear probability changed before execution: "
                f"expected={args.expect_clear_probability:.6f}, "
                f"observed={plan.value.clear_probability:.6f}"
            )

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
            executor_indices = executor.card_indices(state, plan.action)
            if executor_indices != indices:
                raise RuntimeError("hand executor index mapping differs from planner mapping")
            _, locations = executor.locate_hand(state)
            for index in indices:
                location = locations[index]
                print(
                    f"  Screen {index}: {_card_text(state.hand[index])} "
                    f"-> center=({location.center.x:.4f},{location.center.y:.4f})"
                )
            executed_indices = executor.dispatch(plan.action, state)
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
    print(f"Owned Jokers after -> {len(persisted_state.jokers)}")
    for index, joker in enumerate(persisted_state.jokers):
        print(f"  J{index}: {_joker_text(joker)}")
    print("Checkpoint verified -> True")

    if persisted_state.phase == "SELECTING_HAND":
        if persisted_state.boss_name:
            print(
                "Replan blocked -> unsupported Boss Blind: "
                f"{persisted_state.boss_name}"
            )
        else:
            unsupported_after = (
                planner.evaluator.score_outcomes.joker_projector.unsupported_jokers(
                    persisted_state
                )
            )
            if unsupported_after:
                print(
                    "Replan blocked -> unsupported Joker projection(s): "
                    + ", ".join(unsupported_after)
                )
            else:
                try:
                    replanned = planner.plan(persisted_state)
                except (RuntimeError, ValueError) as error:
                    print(f"Replan blocked -> {error}")
                else:
                    _print_plan("Replanned", persisted_state, replanned)
    else:
        print(f"Replan skipped -> phase is {persisted_state.phase}")

    print("Follow-up mouse input sent -> False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
