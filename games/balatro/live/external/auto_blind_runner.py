from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.adaptive_search import (
    AdaptiveBlindSearchConfig,
    AdaptiveRecommendationSummary,
    adaptive_blind_search_schedule,
    stable_discard_consensus,
)
from games.balatro.live.blind_clear_planner import (
    LiveBlindClearPlanner,
    PlannerSearchBudgetExceeded,
)
from games.balatro.live.depth_draw_outcomes import DepthAwarePublicDrawOutcomeModel
from games.balatro.live.synchronizer import BalatroLiveSynchronizer
from games.balatro.live.translator import DefaultBalatroStateTranslator

from .expected_card_locator import locate_card_faces_expected_count
from .hand_mouse import ExternalHandMouseExecutor, HandMouseLayout
from .mouse import BalatroMouseController
from .save_observer import SaveBalatroObserver
from .save_state import BalatroSaveReader


DEFAULT_LAYOUT = "balatro-hand-mouse.json"
PROBABILITY_TOLERANCE = 1e-9


@dataclass(frozen=True)
class _SearchResult:
    config: AdaptiveBlindSearchConfig
    planner: LiveBlindClearPlanner
    plan: object


@dataclass(frozen=True)
class _SearchDecision:
    result: _SearchResult | None
    mode: str


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


def _is_guaranteed(plan) -> bool:
    return bool(plan.exact and plan.value.clear_probability >= 1.0 - 1e-12)


def _accepts(plan, minimum: float | None) -> bool:
    if _is_guaranteed(plan):
        return True
    if minimum is None:
        return False
    return plan.value.clear_probability + PROBABILITY_TOLERANCE >= minimum


def _planner(config: AdaptiveBlindSearchConfig, args) -> LiveBlindClearPlanner:
    return LiveBlindClearPlanner(
        draw_outcomes=DepthAwarePublicDrawOutcomeModel(
            exact_combination_limit=args.exact_limit,
            root_sample_count=config.samples,
            child_sample_count=config.child_samples,
            child_exact_combination_limit=args.child_exact_limit,
        ),
        play_width=config.play_width,
        discard_width=config.discard_width,
        child_play_width=config.child_play_width,
        child_discard_width=config.child_discard_width,
        horizon=config.horizon,
        max_nodes=config.max_nodes,
    )


def _result_key(result: _SearchResult) -> tuple[float, float, float, int]:
    plan = result.plan
    return (
        1.0 if _is_guaranteed(plan) else 0.0,
        float(plan.value.clear_probability),
        float(plan.value.expected_score),
        -result.planner.nodes_evaluated,
    )


def _summary(state, result: _SearchResult) -> AdaptiveRecommendationSummary:
    return AdaptiveRecommendationSummary(
        action=result.plan.action.name,
        indices=_indices(state, result.plan.action),
        clear_probability=float(result.plan.value.clear_probability),
        expected_score=float(result.plan.value.expected_score),
        horizon=result.config.horizon,
        intensified=result.config.max_nodes > 5000,
    )


def _print_plan(prefix: str, state, result: _SearchResult) -> tuple[int, ...]:
    plan = result.plan
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


def _search(state, args) -> _SearchDecision:
    schedule = adaptive_blind_search_schedule(
        hands_remaining=int(state.hands_remaining),
        discards_remaining=int(state.discards_remaining),
        max_horizon=args.max_horizon,
        max_nodes=args.max_search_nodes,
    )
    best: _SearchResult | None = None
    completed: list[_SearchResult] = []
    summaries: list[AdaptiveRecommendationSummary] = []

    print(f"Adaptive search attempts -> {len(schedule)}")
    for attempt, config in enumerate(schedule, start=1):
        planner = _planner(config, args)
        unsupported = planner.evaluator.score_outcomes.joker_projector.unsupported_jokers(state)
        if unsupported:
            raise RuntimeError(
                "planner execution is blocked by unsupported Joker projection(s): "
                + ", ".join(unsupported)
            )

        try:
            plan = planner.plan(state)
        except PlannerSearchBudgetExceeded:
            print(
                f"  Search {attempt} -> horizon={config.horizon} "
                f"samples={config.samples} nodes={planner.nodes_evaluated}/"
                f"{config.max_nodes} BUDGET_EXCEEDED"
            )
            continue

        result = _SearchResult(config=config, planner=planner, plan=plan)
        completed.append(result)
        summaries.append(_summary(state, result))
        print(
            f"  Search {attempt} -> horizon={config.horizon} "
            f"samples={config.samples} nodes={planner.nodes_evaluated}/"
            f"{config.max_nodes} p={plan.value.clear_probability:.6f} "
            f"expected={plan.value.expected_score:.3f} exact={plan.exact}"
        )
        if best is None or _result_key(result) > _result_key(best):
            best = result

        if _accepts(plan, args.min_clear_probability):
            print(f"Adaptive escalation stop -> search {attempt} meets execution policy")
            return _SearchDecision(result=result, mode="threshold")

    if args.allow_consensus_discard and stable_discard_consensus(
        tuple(summaries),
        minimum_agreement=args.consensus_discard_agreement,
    ):
        result = completed[-1]
        indices = _indices(state, result.plan.action)
        print(
            "Adaptive setup consensus -> PASS "
            f"({args.consensus_discard_agreement} deepest completed searches agree on "
            f"DISCARD {','.join(str(index) for index in indices)})"
        )
        return _SearchDecision(result=result, mode="consensus-discard")

    return _SearchDecision(result=best, mode="none")


def _execute_one(state, result: _SearchResult, *, layout, observer, snapshot, translator):
    plan = result.plan
    indices = _indices(state, plan.action)
    mouse = BalatroMouseController(armed=True)
    card_locator = lambda region: locate_card_faces_expected_count(region, len(state.hand))

    with ExternalHandMouseExecutor(
        layout,
        mouse=mouse,
        card_locator=card_locator,
    ) as executor:
        executor_indices = executor.card_indices(state, plan.action)
        if executor_indices != indices:
            raise RuntimeError("hand executor index mapping differs from planner mapping")
        frame, locations = executor.locate_hand(state)
        print(f"Screen/save exact-count guard -> PASS ({len(locations)})")
        for index in indices:
            location = locations[index]
            print(
                f"  Screen {index}: {_card_text(state.hand[index])} "
                f"-> center=({location.center.x:.4f},{location.center.y:.4f})"
            )
        executed_indices = executor.dispatch_with_locations(
            plan.action,
            state,
            frame,
            locations,
        )
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
    return persisted, translator.translate(persisted)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Adaptively search, execute one guarded hand action, checkpoint, and "
            "replan until the blind ends or the configured risk policy blocks."
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
            "minimum sampled clear probability accepted for scored-play execution; "
            "when omitted, only exact guaranteed-clear scored plays may execute"
        ),
    )
    parser.add_argument(
        "--allow-consensus-discard",
        action="store_true",
        help=(
            "allow a setup discard below the scored-play probability threshold only "
            "when the deepest completed searches repeatedly agree on the exact same "
            "discard and their projected outcomes improve with depth"
        ),
    )
    parser.add_argument(
        "--consensus-discard-agreement",
        type=int,
        default=3,
        help="number of deepest completed searches that must agree on a setup discard",
    )
    parser.add_argument("--max-horizon", type=int, default=8)
    parser.add_argument("--max-search-nodes", type=int, default=5000)
    parser.add_argument(
        "--max-actions",
        type=int,
        default=8,
        help="maximum real mouse actions this invocation may send",
    )
    parser.add_argument(
        "--exact-limit",
        type=int,
        default=LiveBlindClearPlanner.DEFAULT_EXACT_DRAW_COMBINATION_LIMIT,
    )
    parser.add_argument("--child-exact-limit", type=int)
    args = parser.parse_args()

    if args.min_clear_probability is not None and not 0.0 <= args.min_clear_probability <= 1.0:
        parser.error("--min-clear-probability must be between 0 and 1")
    if args.consensus_discard_agreement < 2:
        parser.error("--consensus-discard-agreement must be at least 2")
    if args.max_horizon < 1:
        parser.error("--max-horizon must be positive")
    if args.max_search_nodes < 1:
        parser.error("--max-search-nodes must be positive")
    if args.max_actions < 1:
        parser.error("--max-actions must be positive")
    if args.exact_limit < 1:
        parser.error("--exact-limit must be positive")
    if args.child_exact_limit is not None and args.child_exact_limit < 1:
        parser.error("--child-exact-limit must be positive")

    reader = BalatroSaveReader(args.save, profile=args.profile)
    observer = SaveBalatroObserver(reader)
    translator = DefaultBalatroStateTranslator()

    try:
        layout = HandMouseLayout.load(Path(args.layout))
        layout.point_for("play-hand")
        layout.point_for("discard")
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

    actions_sent = 0
    while True:
        snapshot = observer.observe()
        state = translator.translate(snapshot)

        print(f"Save -> {reader.path}")
        print(f"Phase before -> {state.phase}")
        if state.phase == "ROUND_EVAL":
            print("Blind runner -> COMPLETE")
            print(f"Real actions sent -> {actions_sent}")
            print("Follow-up mouse input sent -> False")
            return 0
        if state.phase != "SELECTING_HAND":
            parser.error(f"Balatro save is in {state.phase}, expected SELECTING_HAND")
        if not state.hand:
            parser.error("save contains no visible hand cards")
        if state.boss_name:
            parser.error(
                "adaptive generic runner is blocked until a dedicated Boss Blind "
                f"runner is validated for {state.boss_name}"
            )

        print(f"Score before -> {state.score}")
        print(f"Blind target -> {getattr(state.blind, 'requirement', 0)}")
        print(f"Hands before -> {state.hands_remaining}")
        print(f"Discards before -> {state.discards_remaining}")
        print(f"Owned Jokers -> {len(state.jokers)}")
        for index, joker in enumerate(state.jokers):
            print(f"  J{index}: {_joker_text(joker)}")
        print("Joker projection complete -> True")
        print("Hidden draw order used -> False")

        try:
            decision = _search(state, args)
        except (RuntimeError, ValueError) as error:
            parser.error(str(error))

        result = decision.result
        if result is None:
            print("Execution guard -> BLOCKED")
            print("Reason -> every adaptive search attempt exceeded its node budget")
            print("Mouse input sent -> False")
            return 0

        indices = _print_plan("Selected", state, result)
        accepted = decision.mode in {"threshold", "consensus-discard"}
        if decision.mode == "consensus-discard":
            print(
                "Execution mode -> consensus-discard "
                f"(agreement={args.consensus_discard_agreement}; scored-play minimum="
                + (
                    f"{args.min_clear_probability:.6f}"
                    if args.min_clear_probability is not None
                    else "exact-guaranteed"
                )
                + ")"
            )
        elif _is_guaranteed(result.plan):
            print("Execution mode -> exact-guaranteed")
        elif args.min_clear_probability is not None:
            print(
                "Execution mode -> probabilistic "
                f"(minimum={args.min_clear_probability:.6f})"
            )
        else:
            print("Execution mode -> exact-guaranteed")
        print(f"Execution guard -> {'PASS' if accepted else 'BLOCKED'}")

        if not accepted:
            print("Reason -> no adaptive search met the configured execution policy")
            print("Mouse input sent -> False")
            return 0
        if not args.execute:
            print("Mouse input sent -> False")
            print("Dry run -> adaptive search completed without executing")
            return 0
        if actions_sent >= args.max_actions:
            print("Execution guard -> BLOCKED")
            print(f"Reason -> reached --max-actions {args.max_actions}")
            print("Mouse input sent -> False")
            return 0

        latest = observer.observe()
        if latest.payload.get("save_sha256") != snapshot.payload.get("save_sha256"):
            print("Execution guard -> BLOCKED")
            print("Reason -> save changed during adaptive search; re-run from new checkpoint")
            print("Mouse input sent -> False")
            return 0

        print(
            f"Executing action {actions_sent + 1} -> {result.plan.action.name} "
            + ",".join(str(index) for index in indices)
        )
        try:
            persisted, persisted_state = _execute_one(
                state,
                result,
                layout=layout,
                observer=observer,
                snapshot=snapshot,
                translator=translator,
            )
        except (RuntimeError, TimeoutError, ValueError) as error:
            parser.error(str(error))

        actions_sent += 1
        print(f"Phase after -> {persisted_state.phase}")
        print(f"Score after -> {persisted_state.score}")
        print(f"Hands after -> {persisted_state.hands_remaining}")
        print(f"Discards after -> {persisted_state.discards_remaining}")
        print(f"Hand cards after -> {len(persisted_state.hand)}")
        print(f"Owned Jokers after -> {len(persisted_state.jokers)}")
        for index, joker in enumerate(persisted_state.jokers):
            print(f"  J{index}: {_joker_text(joker)}")
        print("Checkpoint verified -> True")

        if persisted_state.phase == "ROUND_EVAL":
            print("Blind runner -> COMPLETE")
            print(f"Real actions sent -> {actions_sent}")
            print("Follow-up mouse input sent -> False")
            return 0
        if actions_sent >= args.max_actions:
            print("Blind runner -> STOPPED")
            print(f"Reason -> reached --max-actions {args.max_actions}")
            print("Follow-up mouse input sent -> False")
            return 0

        print("Replan -> adaptive search from authoritative checkpoint")
        print("---")


if __name__ == "__main__":
    raise SystemExit(main())
