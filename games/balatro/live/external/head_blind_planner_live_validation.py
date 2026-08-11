from __future__ import annotations

import argparse

from games.balatro.live.blind_clear_planner import PlannerSearchBudgetExceeded
from games.balatro.live.depth_draw_outcomes import DepthAwarePublicDrawOutcomeModel
from games.balatro.live.external.save_observer import SaveBalatroObserver
from games.balatro.live.external.save_state import BalatroSaveReader
from games.balatro.live.head_blind_planner import HeadBlindClearPlanner
from games.balatro.live.translator import DefaultBalatroStateTranslator


def _indices(state, action) -> tuple[int, ...]:
    selected_ids = {id(card) for card in action.cards}
    return tuple(
        index for index, card in enumerate(state.hand) if id(card) in selected_ids
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read the vanilla Balatro save and preview a bounded The Head planner. "
            "This validator never sends mouse input."
        )
    )
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
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

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    state = DefaultBalatroStateTranslator().translate(observer.observe())

    print(f"Save -> {reader.path}")
    print(f"Phase -> {state.phase}")
    print(f"Boss -> {state.boss_name or 'none'}")
    print(f"Score -> {state.score}")
    print(f"Blind target -> {getattr(state.blind, 'requirement', 0)}")
    print(f"Hands -> {state.hands_remaining}")
    print(f"Discards -> {state.discards_remaining}")

    if state.phase != "SELECTING_HAND":
        print("Planner ready -> False")
        print(f"Reason -> current phase is {state.phase}")
        print("Mouse input sent -> False")
        return 0
    if state.boss_name != HeadBlindClearPlanner.BOSS_NAME:
        print("Boss modifier support -> False")
        print("Planner ready -> False")
        print(
            f"Reason -> expected {HeadBlindClearPlanner.BOSS_NAME}, "
            f"observed {state.boss_name or 'none'}"
        )
        print("Mouse input sent -> False")
        return 0

    planner = HeadBlindClearPlanner(
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
    scorer = planner.evaluator.scorer

    print("Boss modifier support -> True")
    print(
        "Boss rule -> Hearts and Wild cards are debuffed; they still form poker "
        "hands but add no card scoring/held effects"
    )
    print(f"Visible hand cards -> {len(state.hand)}")
    for index, card in enumerate(state.hand):
        suffix = " [DEBUFFED]" if scorer.is_card_debuffed(card) else ""
        print(f"  {index}: {_card_text(card)}{suffix}")
    print(f"Public remaining deck cards -> {len(state.deck)}")
    print(f"Owned Jokers -> {len(state.jokers)}")
    for index, joker in enumerate(state.jokers):
        print(f"  J{index}: {_joker_text(joker)}")
    print(f"Planner horizon -> {args.horizon} actions")
    print(f"Planner node budget -> {args.max_nodes}")
    print(f"Root sampled draw branches -> {args.samples}")
    print(f"Child sampled draw branches -> {args.child_samples}")

    unsupported = planner.evaluator.score_outcomes.joker_projector.unsupported_jokers(
        state
    )
    print(f"Joker projection complete -> {not unsupported}")
    print(
        "Unsupported Joker projections -> "
        + (", ".join(unsupported) if unsupported else "none")
    )
    if unsupported:
        print("Planner ready -> False")
        print("Reason -> unsupported Joker projection")
        print("Mouse input sent -> False")
        return 0

    try:
        plan = planner.plan(state)
    except PlannerSearchBudgetExceeded as error:
        print("Planner ready -> False")
        print(f"Reason -> {error}")
        print(f"Planner nodes evaluated -> {planner.nodes_evaluated}")
        print("Mouse input sent -> False")
        return 0
    except (RuntimeError, ValueError) as error:
        parser.error(str(error))

    indices = _indices(state, plan.action)
    print("Planner ready -> True")
    print(f"Recommended -> {plan.action.name}")
    print("Selected indices -> " + ",".join(str(index) for index in indices))
    for index in indices:
        card = state.hand[index]
        suffix = " [DEBUFFED]" if scorer.is_card_debuffed(card) else ""
        print(f"  {index}: {_card_text(card)}{suffix}")
    print(f"Horizon clear probability -> {plan.value.clear_probability:.6f}")
    print(f"Expected horizon score -> {plan.value.expected_score:.3f}")
    print(f"Expected hands remaining -> {plan.value.expected_hands_remaining:.3f}")
    print(f"Expected discards remaining -> {plan.value.expected_discards_remaining:.3f}")
    print(f"Planner nodes evaluated -> {planner.nodes_evaluated}")
    print(f"Draw/Joker branches exact -> {plan.exact}")
    print("Hidden draw order used -> False")
    print("Mouse input sent -> False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
