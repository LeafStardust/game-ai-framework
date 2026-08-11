from __future__ import annotations

import argparse

from games.balatro.actions import PLAY_CARDS, DISCARD_CARDS
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.consumable_escape import (
    SunConsumableEscapePlanner,
    judgement_live_block_reason,
)
from games.balatro.live.translator import DefaultBalatroStateTranslator

from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only live validator for deterministic The Sun escape planning. "
            "It never sends mouse input."
        )
    )
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
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

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    state = DefaultBalatroStateTranslator().translate(observer.observe())

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
            f"(live_id={getattr(consumable, 'live_id', None)})"
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

    print(f"The Sun slot -> C{recommendation.consumable_index}")
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

    print("Execution mode -> read-only consumable planning")
    print("Mouse input sent -> False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
