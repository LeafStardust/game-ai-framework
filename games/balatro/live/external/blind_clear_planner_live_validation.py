from __future__ import annotations

import argparse

from games.balatro.live.blind_clear_planner import (
    LiveBlindClearPlanner,
    LiveBlindPlan,
    PlannerSearchBudgetExceeded,
)
from games.balatro.live.external.save_observer import SaveBalatroObserver
from games.balatro.live.external.save_state import BalatroSaveReader
from games.balatro.live.translator import DefaultBalatroStateTranslator


def _indices(state, action) -> tuple[int, ...]:
    identities = {id(card) for card in action.cards}
    return tuple(
        index
        for index, card in enumerate(state.hand)
        if id(card) in identities
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


def _consumable_text(consumable) -> str:
    return str(
        getattr(consumable, "name", None)
        or getattr(consumable, "label", None)
        or type(consumable).__name__
    )


def _rank_plans(planner, state) -> list[LiveBlindPlan]:
    planner.reset_search_stats()
    candidates = planner._candidate_actions(
        state,
        allow_discards=planner.horizon > 1,
    )
    if not candidates:
        raise RuntimeError("no live blind-clear candidate action is available")

    estimates = [
        planner._estimate_action(state, action, planner.horizon)
        for action in candidates
    ]
    estimates.sort(key=planner._estimate_key, reverse=True)
    return [
        LiveBlindPlan(
            action=estimate.action,
            value=estimate.value,
            horizon=planner.horizon,
            exact=estimate.exact,
            candidate_count=len(candidates),
        )
        for estimate in estimates
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read the vanilla Balatro save and preview the bounded public-state "
            "blind-clear planner. This validator never sends mouse input."
        )
    )
    parser.add_argument("--save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--play-width", type=int, default=6)
    parser.add_argument("--discard-width", type=int, default=4)
    parser.add_argument("--child-play-width", type=int)
    parser.add_argument("--child-discard-width", type=int)
    parser.add_argument("--horizon", type=int, default=2)
    parser.add_argument("--max-nodes", type=int)
    parser.add_argument("--top", type=int, default=10)
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
    args = parser.parse_args()

    if args.horizon < 1:
        parser.error("--horizon must be at least 1")
    if args.child_play_width is not None and args.child_play_width < 1:
        parser.error("--child-play-width must be positive")
    if args.child_discard_width is not None and args.child_discard_width < 0:
        parser.error("--child-discard-width cannot be negative")
    if args.max_nodes is not None and args.max_nodes < 1:
        parser.error("--max-nodes must be positive")

    # Deeper diagnostics are automatically bounded unless the caller supplies a
    # tighter/looser explicit budget. Horizon 1-2 retains historical behavior.
    max_nodes = args.max_nodes
    if max_nodes is None and args.horizon > 2:
        max_nodes = 1000

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    snapshot = observer.observe()
    state = DefaultBalatroStateTranslator().translate(snapshot)

    blind_type = getattr(getattr(state, "blind", None), "type", None)
    blind_type_text = getattr(blind_type, "value", str(blind_type) if blind_type else "none")

    print(f"Save -> {reader.path}")
    print(f"Phase -> {state.phase}")
    print(f"Score -> {state.score}")
    print(f"Blind type -> {blind_type_text}")
    print(f"Boss -> {state.boss_name or 'none'}")
    print(f"Blind target -> {getattr(state.blind, 'requirement', 0)}")
    print(f"Hands -> {state.hands_remaining}")
    print(f"Discards -> {state.discards_remaining}")
    print(f"Visible hand cards -> {len(state.hand)}")
    for index, card in enumerate(state.hand):
        print(f"  {index}: {_card_text(card)}")
    print(f"Public remaining deck cards -> {len(state.deck)}")
    print(f"Owned Jokers -> {len(state.jokers)}")
    for index, joker in enumerate(state.jokers):
        print(f"  J{index}: {_joker_text(joker)}")
    print(f"Owned consumables -> {len(state.consumables)}")
    for index, consumable in enumerate(state.consumables):
        print(f"  C{index}: {_consumable_text(consumable)}")
    print(f"Planner play width -> {args.play_width}")
    print(f"Planner discard width -> {args.discard_width}")
    print(
        "Planner child play width -> "
        f"{args.child_play_width if args.child_play_width is not None else args.play_width}"
    )
    print(
        "Planner child discard width -> "
        f"{args.child_discard_width if args.child_discard_width is not None else args.discard_width}"
    )
    print(f"Planner horizon -> {args.horizon} actions")
    print(f"Planner node budget -> {max_nodes if max_nodes is not None else 'unbounded'}")
    print(f"Exact draw combination limit -> {args.exact_limit}")
    print(f"Sampled draw branches -> {args.samples}")

    if state.phase != "SELECTING_HAND":
        print("Planner ready -> False")
        print(f"Reason -> current phase is {state.phase}")
        print("Mouse input sent -> False")
        return 0

    if state.boss_name:
        print("Boss modifier support -> False")
        print("Planner ready -> False")
        print(
            "Reason -> boss-blind modifier integration is not yet validated for "
            f"{state.boss_name}"
        )
        print("Mouse input sent -> False")
        return 0

    from games.balatro.live.draw_outcomes import PublicDrawOutcomeModel

    planner = LiveBlindClearPlanner(
        draw_outcomes=PublicDrawOutcomeModel(
            exact_combination_limit=args.exact_limit,
            sample_count=args.samples,
        ),
        play_width=args.play_width,
        discard_width=args.discard_width,
        child_play_width=args.child_play_width,
        child_discard_width=args.child_discard_width,
        horizon=args.horizon,
        max_nodes=max_nodes,
    )
    unsupported = planner.evaluator.score_outcomes.joker_projector.unsupported_jokers(
        state
    )
    print(f"Joker projection complete -> {not unsupported}")
    print(
        "Unsupported Joker projections -> "
        + (", ".join(unsupported) if unsupported else "none")
    )

    try:
        ranked = _rank_plans(planner, state)
    except PlannerSearchBudgetExceeded as error:
        print("Planner ready -> False")
        print(f"Reason -> {error}")
        print(f"Planner nodes evaluated -> {planner.nodes_evaluated}")
        print("Mouse input sent -> False")
        return 0
    except (RuntimeError, ValueError) as error:
        parser.error(str(error))

    plan = ranked[0]
    indices = _indices(state, plan.action)
    print(f"Recommended -> {plan.action.name}")
    print("Selected indices -> " + ",".join(str(index) for index in indices))
    for index in indices:
        print(f"  {index}: {_card_text(state.hand[index])}")
    print(f"Horizon clear probability -> {plan.value.clear_probability:.6f}")
    print(f"Expected horizon progress -> {plan.value.expected_progress:.6f}")
    print(f"Expected horizon score -> {plan.value.expected_score:.3f}")
    print(f"Expected hands remaining -> {plan.value.expected_hands_remaining:.3f}")
    print(f"Expected discards remaining -> {plan.value.expected_discards_remaining:.3f}")
    print(f"Candidate actions evaluated -> {plan.candidate_count}")
    print(f"Planner nodes evaluated -> {planner.nodes_evaluated}")
    print(f"Draw/Joker branches exact -> {plan.exact}")

    print("Ranked root candidates:")
    for rank, candidate in enumerate(ranked[: max(1, args.top)], start=1):
        candidate_indices = _indices(state, candidate.action)
        value = candidate.value
        print(
            f"  {rank}. {candidate.action.name} "
            f"indices={','.join(str(index) for index in candidate_indices)} "
            f"clear={value.clear_probability:.6f} "
            f"progress={value.expected_progress:.6f} "
            f"score={value.expected_score:.3f} "
            f"hands={value.expected_hands_remaining:.3f} "
            f"discards={value.expected_discards_remaining:.3f} "
            f"exact={candidate.exact}"
        )

    print("Hidden draw order used -> False")
    print("Mouse input sent -> False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
