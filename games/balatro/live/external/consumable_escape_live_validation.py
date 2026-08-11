from __future__ import annotations

import argparse
from pathlib import Path

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.consumable_escape import (
    SunConsumableEscapePlanner,
    judgement_live_block_reason,
)
from games.balatro.live.synchronizer import BalatroLiveSynchronizer
from games.balatro.live.translator import DefaultBalatroStateTranslator

from .consumable_mouse import (
    ConsumableMouseLayout,
    ExternalSunMouseExecutor,
)
from .mouse import BalatroMouseController
from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader


DEFAULT_LAYOUT = "balatro-consumable-mouse.json"
PROBABILITY_TOLERANCE = 1e-9


def _card_text(card) -> str:
    parts = [str(card.rank), str(card.suit)]
    if getattr(card, "enhancement", None):
        parts.append(str(card.enhancement))
    if getattr(card, "edition", None):
        parts.append(str(card.edition))
    if getattr(card, "seal", None):
        parts.append(str(card.seal))
    return " / ".join(parts)


def _plan_indices(state, action) -> tuple[int, ...]:
    selected = list(action.cards)
    result = []
    for index, card in enumerate(state.hand):
        match = next((item for item in selected if item is card), None)
        if match is None:
            live_id = getattr(card, "live_id", None)
            match = next(
                (
                    item
                    for item in selected
                    if live_id is not None
                    and getattr(item, "live_id", None) == live_id
                ),
                None,
            )
        if match is not None:
            result.append(index)
            selected.remove(match)
    return tuple(result)


def _is_accepted(recommendation, minimum: float | None) -> bool:
    if recommendation.guaranteed_clear:
        return True
    if minimum is None:
        return False
    return recommendation.clear_probability + PROBABILITY_TOLERANCE >= minimum


def _card_fingerprint(card, *, include_suit: bool = True) -> tuple:
    values = [
        getattr(card, "rank", None),
        getattr(card, "enhancement", None),
        getattr(card, "edition", None),
        getattr(card, "seal", None),
    ]
    if include_suit:
        values.insert(1, getattr(card, "suit", None))
    return tuple(values)


def verify_sun_checkpoint(
    before,
    after,
    *,
    target_live_ids: tuple[object, ...],
    sun_live_id: object,
) -> str | None:
    """Return a reconciliation failure reason, or None for a validated Sun use."""

    if after.phase != "SELECTING_HAND":
        return f"phase changed to {after.phase}, expected SELECTING_HAND"
    if int(after.score) != int(before.score):
        return f"score changed during The Sun use: {before.score} -> {after.score}"
    if int(after.hands_remaining) != int(before.hands_remaining):
        return (
            "hands changed during The Sun use: "
            f"{before.hands_remaining} -> {after.hands_remaining}"
        )
    if int(after.discards_remaining) != int(before.discards_remaining):
        return (
            "discards changed during The Sun use: "
            f"{before.discards_remaining} -> {after.discards_remaining}"
        )
    if len(after.hand) != len(before.hand):
        return f"hand size changed during The Sun use: {len(before.hand)} -> {len(after.hand)}"
    if len(after.consumables) != len(before.consumables) - 1:
        return (
            "held consumable count did not decrease by exactly one: "
            f"{len(before.consumables)} -> {len(after.consumables)}"
        )
    if any(
        getattr(consumable, "live_id", None) == sun_live_id
        for consumable in after.consumables
    ):
        return "the consumed The Sun live_id is still present after the checkpoint"

    before_cards = {
        getattr(card, "live_id", None): card
        for card in before.hand
        if getattr(card, "live_id", None) is not None
    }
    after_cards = {
        getattr(card, "live_id", None): card
        for card in after.hand
        if getattr(card, "live_id", None) is not None
    }
    if set(before_cards) != set(after_cards):
        return "hand live_id set changed during The Sun use"

    targets = set(target_live_ids)
    if len(targets) != len(target_live_ids) or None in targets:
        return "The Sun target live_ids are not stable and unique"

    for live_id, before_card in before_cards.items():
        after_card = after_cards[live_id]
        if live_id in targets:
            if getattr(after_card, "suit", None) != "Hearts":
                return f"The Sun target live_id {live_id} did not become Hearts"
            if _card_fingerprint(after_card, include_suit=False) != _card_fingerprint(
                before_card,
                include_suit=False,
            ):
                return f"The Sun target live_id {live_id} changed non-suit card fields"
        elif _card_fingerprint(after_card) != _card_fingerprint(before_card):
            return f"non-target live_id {live_id} changed during The Sun use"

    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Plan deterministic The Sun blind escapes and optionally execute exactly "
            "one guarded consumable use through normal mouse input."
        )
    )
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--layout", default=DEFAULT_LAYOUT)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--min-clear-probability",
        type=float,
        help=(
            "minimum sampled post-Sun blind-clear probability accepted for execution; "
            "when omitted, only an exact guaranteed-clear Sun plan may execute"
        ),
    )
    parser.add_argument("--horizon", type=int)
    parser.add_argument("--samples", type=int, default=12)
    parser.add_argument("--child-samples", type=int, default=2)
    parser.add_argument("--play-width", type=int, default=6)
    parser.add_argument("--discard-width", type=int, default=1)
    parser.add_argument("--child-play-width", type=int, default=2)
    parser.add_argument("--child-discard-width", type=int, default=1)
    parser.add_argument("--target-width", type=int, default=16)
    parser.add_argument("--max-nodes", type=int, default=10000)
    parser.add_argument(
        "--exact-limit",
        type=int,
        default=LiveBlindClearPlanner.DEFAULT_EXACT_DRAW_COMBINATION_LIMIT,
    )
    parser.add_argument("--child-exact-limit", type=int)
    args = parser.parse_args()

    for name in (
        "samples",
        "child_samples",
        "play_width",
        "child_play_width",
        "target_width",
        "max_nodes",
        "exact_limit",
    ):
        if getattr(args, name) < 1:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    for name in ("discard_width", "child_discard_width"):
        if getattr(args, name) < 0:
            parser.error(f"--{name.replace('_', '-')} cannot be negative")
    if args.horizon is not None and args.horizon < 1:
        parser.error("--horizon must be positive")
    if args.child_exact_limit is not None and args.child_exact_limit < 1:
        parser.error("--child-exact-limit must be positive")
    if (
        args.min_clear_probability is not None
        and not 0.0 <= args.min_clear_probability <= 1.0
    ):
        parser.error("--min-clear-probability must be between 0 and 1")

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    translator = DefaultBalatroStateTranslator()
    snapshot = observer.observe()
    state = translator.translate(snapshot)

    print(f"Save -> {reader.path}")
    print(f"Phase before -> {state.phase}")
    if state.phase != "SELECTING_HAND":
        parser.error(f"Balatro save is in {state.phase}, expected SELECTING_HAND")

    print(f"Score before -> {state.score}")
    print(f"Blind target -> {getattr(state.blind, 'requirement', 0)}")
    print(f"Hands before -> {state.hands_remaining}")
    print(f"Discards before -> {state.discards_remaining}")
    print(f"Held consumables -> {len(state.consumables)}")
    for index, consumable in enumerate(state.consumables):
        print(
            f"  C{index}: {getattr(consumable, 'name', type(consumable).__name__)} "
            f"(live_id={getattr(consumable, 'live_id', None)}, "
            f"area_index={getattr(consumable, 'area_index', None)})"
        )

    judgement_reason = judgement_live_block_reason(state)
    if judgement_reason:
        print(f"Judgement planning -> BLOCKED ({judgement_reason})")

    action_budget = int(state.hands_remaining) + int(state.discards_remaining)
    horizon = args.horizon if args.horizon is not None else max(1, action_budget)
    horizon = min(horizon, max(1, action_budget))
    print(f"The Sun planner horizon -> {horizon} actions")
    print("Hidden draw order used -> False")

    try:
        recommendation = SunConsumableEscapePlanner(
            horizon=horizon,
            exact_combination_limit=args.exact_limit,
            root_sample_count=args.samples,
            child_sample_count=args.child_samples,
            child_exact_combination_limit=args.child_exact_limit,
            play_width=args.play_width,
            discard_width=args.discard_width,
            child_play_width=args.child_play_width,
            child_discard_width=args.child_discard_width,
            max_nodes=args.max_nodes,
            target_width=args.target_width,
        ).plan(state)
    except (RuntimeError, ValueError) as error:
        print("The Sun escape guard -> BLOCKED")
        print(f"Reason -> {error}")
        print("Mouse input sent -> False")
        return 0

    sun = state.consumables[recommendation.consumable_index]
    print(
        f"The Sun slot -> C{recommendation.consumable_index} "
        f"(area_index={getattr(sun, 'area_index', None)})"
    )
    print(
        "The Sun target indices -> "
        + ",".join(str(index) for index in recommendation.target_indices)
    )
    for index in recommendation.target_indices:
        print(f"  {index}: {_card_text(state.hand[index])} -> Hearts")
    print(f"Targets considered -> {recommendation.targets_considered}")
    print(f"Targets fully searched -> {recommendation.targets_searched}")
    print(f"Targets budget exceeded -> {recommendation.targets_budget_exceeded}")
    print(f"Planner nodes evaluated -> {recommendation.nodes_evaluated}")
    print(f"Projected clear probability -> {recommendation.clear_probability:.6f}")
    print(f"Projected expected score -> {recommendation.expected_score:.3f}")
    print(f"Projected exact -> {recommendation.exact}")
    print(f"Projected guaranteed clear -> {recommendation.guaranteed_clear}")

    continuation = recommendation.plan.action
    continuation_indices = _plan_indices(state, continuation)
    print(f"Projected first continuation -> {continuation.name}")
    print(
        "Projected continuation indices -> "
        + ",".join(str(index) for index in continuation_indices)
    )
    if continuation.name in {PLAY_CARDS, DISCARD_CARDS}:
        for index in continuation_indices:
            print(f"  {index}: {_card_text(state.hand[index])}")

    accepted = _is_accepted(recommendation, args.min_clear_probability)
    if recommendation.guaranteed_clear:
        print("Execution mode -> exact-guaranteed")
    elif args.min_clear_probability is not None:
        print(
            "Execution mode -> probabilistic "
            f"(minimum={args.min_clear_probability:.6f})"
        )
    else:
        print("Execution mode -> exact-guaranteed")
    print(f"Execution guard -> {'PASS' if accepted else 'BLOCKED'}")

    if not args.execute:
        print("Mouse input sent -> False")
        print("Dry run -> The Sun escape planning completed without executing")
        return 0
    if not accepted:
        print("Reason -> post-Sun plan does not meet the configured execution policy")
        print("Mouse input sent -> False")
        return 0

    try:
        area_index = int(getattr(sun, "area_index"))
        layout = ConsumableMouseLayout.load(Path(args.layout))
        layout.point_for_slot(area_index)
        layout.use_point_for_slot(area_index)
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        parser.error(str(error))

    sun_live_id = getattr(sun, "live_id", None)
    if sun_live_id is None:
        parser.error("The Sun has no stable live_id in the save observation")
    target_live_ids = tuple(
        getattr(state.hand[index], "live_id", None)
        for index in recommendation.target_indices
    )
    if None in target_live_ids or len(set(target_live_ids)) != len(target_live_ids):
        parser.error("The Sun target cards do not have stable unique live_ids")

    latest = observer.observe()
    if latest.payload.get("save_sha256") != snapshot.payload.get("save_sha256"):
        print("Execution guard -> BLOCKED")
        print("Reason -> save changed during The Sun planning; re-run from new checkpoint")
        print("Mouse input sent -> False")
        return 0

    print(
        "Executing consumable -> The Sun targets "
        + ",".join(str(index) for index in recommendation.target_indices)
    )
    mouse = BalatroMouseController(armed=True)
    try:
        with ExternalSunMouseExecutor(layout, mouse=mouse) as executor:
            executor.dispatch(state, sun, recommendation.target_indices)
    except (RuntimeError, ValueError) as error:
        parser.error(str(error))

    print("Mouse input sent -> True")
    print("Waiting for save checkpoint -> The Sun consumed and target suits changed")
    try:
        persisted = BalatroLiveSynchronizer(
            observer,
            poll_interval=0.05,
            timeout=20.0,
        ).wait_for_change(
            snapshot,
            phases={"SELECTING_HAND"},
            require_complete=False,
        )
    except TimeoutError as error:
        parser.error(str(error))
    after = translator.translate(persisted)

    reason = verify_sun_checkpoint(
        state,
        after,
        target_live_ids=target_live_ids,
        sun_live_id=sun_live_id,
    )
    if reason is not None:
        print("Checkpoint verified -> False")
        print(f"Reason -> {reason}")
        print("Follow-up mouse input sent -> False")
        return 2

    print(f"Phase after -> {after.phase}")
    print(f"Score after -> {after.score}")
    print(f"Hands after -> {after.hands_remaining}")
    print(f"Discards after -> {after.discards_remaining}")
    print(f"Held consumables after -> {len(after.consumables)}")
    print("Checkpoint verified -> True")
    print("The Sun live execution -> VALIDATED")
    print("Follow-up mouse input sent -> False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
