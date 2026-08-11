from __future__ import annotations

import argparse
from pathlib import Path

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.blind_clear_planner import PlannerSearchBudgetExceeded
from games.balatro.live.depth_draw_outcomes import DepthAwarePublicDrawOutcomeModel
from games.balatro.live.head_blind_planner import HeadBlindClearPlanner
from games.balatro.live.synchronizer import BalatroLiveSynchronizer
from games.balatro.live.translator import DefaultBalatroStateTranslator

from .expected_card_locator import (
    _locations_form_uniform_grid,
    locate_card_faces_expected_count,
)
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
    if not indices or any(index < 0 for index in indices):
        raise ValueError("--expect-indices must contain non-negative integers")
    return indices


def _indices(state, action) -> tuple[int, ...]:
    selected_ids = {id(card) for card in action.cards}
    return tuple(index for index, card in enumerate(state.hand) if id(card) in selected_ids)


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


def _head_card_locator(expected_count: int):
    """Return the save-backed structural locator validated for The Head.

    Boss-debuffed cards can be visually dim enough for ordinary bright-face
    detection to miss them or return malformed mixed components. The expected-
    count locator reconstructs a hand only when it can produce exactly the
    authoritative save count on a uniform Balatro card grid; otherwise execution
    fails closed before any click is sent.
    """

    def locate(region):
        locations = locate_card_faces_expected_count(region, expected_count)
        if len(locations) != expected_count:
            return locations
        if not _locations_form_uniform_grid(locations):
            return []
        return locations

    return locate


def _planner(args) -> HeadBlindClearPlanner:
    return HeadBlindClearPlanner(
        draw_outcomes=DepthAwarePublicDrawOutcomeModel(
            exact_combination_limit=args.exact_limit,
            root_sample_count=args.samples,
            child_sample_count=args.child_samples,
            child_exact_combination_limit=args.child_exact_limit,
        ),
        play_width=args.play_width,
        discard_width=args.discard_width,
        child_play_width=args.child_play_width,
        child_discard_width=args.child_discard_width,
        horizon=args.horizon,
        max_nodes=args.max_nodes,
    )


def _is_guaranteed(plan) -> bool:
    return plan.exact and plan.value.clear_probability >= 1.0 - 1e-12


def _print_plan(prefix: str, state, plan, scorer) -> tuple[int, ...]:
    indices = _indices(state, plan.action)
    print(f"{prefix} -> {plan.action.name}")
    print(f"{prefix} indices -> " + ",".join(str(index) for index in indices))
    for index in indices:
        card = state.hand[index]
        suffix = " [DEBUFFED]" if scorer.is_card_debuffed(card) else ""
        print(f"  {index}: {_card_text(card)}{suffix}")
    print(f"{prefix} clear probability -> {plan.value.clear_probability:.6f}")
    print(f"{prefix} expected score -> {plan.value.expected_score:.3f}")
    print(f"{prefix} exact -> {plan.exact}")
    print(f"{prefix} guaranteed clear -> {_is_guaranteed(plan)}")
    return indices


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or execute exactly one guarded The Head planner action, wait "
            "for the authoritative save checkpoint, then replan without automatically "
            "executing the follow-up action."
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
    parser.add_argument("--samples", type=int, default=8)
    parser.add_argument("--child-samples", type=int, default=1)
    parser.add_argument(
        "--exact-limit",
        type=int,
        default=HeadBlindClearPlanner.DEFAULT_EXACT_DRAW_COMBINATION_LIMIT,
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
    if args.max_nodes < 1:
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

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    translator = DefaultBalatroStateTranslator()
    snapshot = observer.observe()
    state = translator.translate(snapshot)

    if state.phase != "SELECTING_HAND":
        parser.error(f"Balatro save is in {state.phase}, expected SELECTING_HAND")
    if not state.hand:
        parser.error("save contains no visible hand cards")
    if state.boss_name != HeadBlindClearPlanner.BOSS_NAME:
        parser.error(
            f"expected {HeadBlindClearPlanner.BOSS_NAME}, observed {state.boss_name!r}"
        )

    planner = _planner(args)
    scorer = planner.evaluator.scorer
    unsupported = planner.evaluator.score_outcomes.joker_projector.unsupported_jokers(state)
    if unsupported:
        parser.error(
            "planner execution is blocked by unsupported Joker projection(s): "
            + ", ".join(unsupported)
        )

    try:
        plan = planner.plan(state)
    except PlannerSearchBudgetExceeded as error:
        print(f"Save -> {reader.path}")
        print(f"Phase before -> {state.phase}")
        print("Execution guard -> BLOCKED")
        print(f"Reason -> {error}")
        print(f"Planner nodes evaluated -> {planner.nodes_evaluated}")
        print("Mouse input sent -> False")
        return 0
    except (RuntimeError, ValueError) as error:
        parser.error(str(error))

    print(f"Save -> {reader.path}")
    print(f"Phase before -> {state.phase}")
    print(f"Boss -> {state.boss_name}")
    print("Boss modifier support -> True")
    print("Boss rule -> Hearts and Wild cards are debuffed")
    print(f"Score before -> {state.score}")
    print(f"Blind target -> {getattr(state.blind, 'requirement', 0)}")
    print(f"Hands before -> {state.hands_remaining}")
    print(f"Discards before -> {state.discards_remaining}")
    print(f"Planner horizon -> {args.horizon} actions")
    print(f"Planner nodes evaluated -> {planner.nodes_evaluated}")
    print(f"Owned Jokers -> {len(state.jokers)}")
    for index, joker in enumerate(state.jokers):
        print(f"  J{index}: {_joker_text(joker)}")
    print("Joker projection complete -> True")
    print("Hidden draw order used -> False")
    indices = _print_plan("Recommended", state, plan, scorer)

    guaranteed = _is_guaranteed(plan)
    probabilistic = (
        args.allow_probabilistic
        and args.min_clear_probability is not None
        and plan.value.clear_probability + PROBABILITY_TOLERANCE >= args.min_clear_probability
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
        print("Reason -> recommendation is not allowed by the selected execution mode")
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
        if abs(plan.value.clear_probability - args.expect_clear_probability) > PROBABILITY_TOLERANCE:
            parser.error(
                "planner clear probability changed before execution: "
                f"expected={args.expect_clear_probability:.6f}, "
                f"observed={plan.value.clear_probability:.6f}"
            )

    try:
        layout = HandMouseLayout.load(Path(args.layout))
        layout.point_for("play-hand")
        layout.point_for("discard")
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    mouse = BalatroMouseController(armed=True)
    card_locator = _head_card_locator(len(state.hand))
    try:
        with ExternalHandMouseExecutor(
            layout,
            mouse=mouse,
            card_locator=card_locator,
        ) as executor:
            executor_indices = executor.card_indices(state, plan.action)
            if executor_indices != indices:
                raise RuntimeError("hand executor index mapping differs from planner mapping")
            _, locations = executor.locate_hand(state)
            if not _locations_form_uniform_grid(locations):
                raise RuntimeError(
                    "Head execution blocked: located cards do not form a uniform grid"
                )
            print("Screen grid-spacing guard -> PASS")
            for index in indices:
                location = locations[index]
                card = state.hand[index]
                suffix = " [DEBUFFED]" if scorer.is_card_debuffed(card) else ""
                print(
                    f"  Screen {index}: {_card_text(card)}{suffix} "
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
        if persisted_state.boss_name != HeadBlindClearPlanner.BOSS_NAME:
            print(f"Replan blocked -> unexpected boss {persisted_state.boss_name!r}")
        else:
            unsupported_after = planner.evaluator.score_outcomes.joker_projector.unsupported_jokers(
                persisted_state
            )
            if unsupported_after:
                print(
                    "Replan blocked -> unsupported Joker projection(s): "
                    + ", ".join(unsupported_after)
                )
            else:
                try:
                    replanned = planner.plan(persisted_state)
                except (PlannerSearchBudgetExceeded, RuntimeError, ValueError) as error:
                    print(f"Replan blocked -> {error}")
                else:
                    _print_plan("Replanned", persisted_state, replanned, planner.evaluator.scorer)
    else:
        print(f"Replan skipped -> phase is {persisted_state.phase}")

    print("Follow-up mouse input sent -> False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
