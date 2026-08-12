from __future__ import annotations

import argparse

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.depth_draw_outcomes import DepthAwarePublicDrawOutcomeModel
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.live.hand_action_policy import (
    HandActionThresholds,
    LiveHandActionDecisionEngine,
    LiveHandActionThresholdPolicy,
)
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.playbook import default_balatro_playbooks

from .live_memory_observer import LiveMemoryBalatroObserver


def _indices(state, action) -> tuple[int, ...]:
    selected_ids = {id(card) for card in action.cards}
    return tuple(
        index
        for index, card in enumerate(state.hand)
        if id(card) in selected_ids
    )


def _card_text(card) -> str:
    parts = [str(card.rank), str(card.suit)]
    for field in ("enhancement", "edition", "seal"):
        value = getattr(card, field, None)
        if value:
            parts.append(str(value))
    return " / ".join(parts)


def _plan_text(state, plan) -> str:
    indices = _indices(state, plan.action)
    value = plan.value
    return (
        f"{plan.action.name} indices={indices} "
        f"clear={value.clear_probability:.6f} "
        f"progress={value.expected_progress:.6f} "
        f"score={value.expected_score:.3f} "
        f"hands={value.expected_hands_remaining:.3f} "
        f"discards={value.expected_discards_remaining:.3f} "
        f"exact={plan.exact}"
    )


def _target(state) -> int:
    blind = getattr(state, "blind", None)
    return int(getattr(blind, "requirement", 0)) if blind is not None else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only D1 live hand-action validation. Ranks Play/Discard candidates "
            "from direct Balatro process memory, applies the dedicated D1 threshold "
            "block, and sends no mouse input."
        )
    )
    parser.add_argument("--horizon", type=int, default=2)
    parser.add_argument("--play-width", type=int, default=6)
    parser.add_argument("--discard-width", type=int, default=4)
    parser.add_argument("--child-play-width", type=int, default=4)
    parser.add_argument("--child-discard-width", type=int, default=2)
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--child-samples", type=int, default=24)
    parser.add_argument("--exact-limit", type=int, default=128)
    parser.add_argument("--child-exact-limit", type=int, default=8)
    parser.add_argument("--max-nodes", type=int, default=2500)
    args = parser.parse_args()

    if args.horizon < 1:
        parser.error("--horizon must be at least 1")
    if args.play_width < 1:
        parser.error("--play-width must be positive")
    if args.discard_width < 0:
        parser.error("--discard-width cannot be negative")
    if args.child_play_width < 1:
        parser.error("--child-play-width must be positive")
    if args.child_discard_width < 0:
        parser.error("--child-discard-width cannot be negative")
    for name in ("samples", "child_samples", "exact_limit", "child_exact_limit", "max_nodes"):
        if getattr(args, name) < 1:
            parser.error(f"--{name.replace('_', '-')} must be positive")

    try:
        with LiveMemoryBalatroObserver() as observer:
            snapshot = observer.observe()
            state = DefaultBalatroStateTranslator().translate(snapshot)
            if state.phase != "SELECTING_HAND":
                raise RuntimeError(
                    f"D1 live validation requires SELECTING_HAND, observed {state.phase}"
                )

            playbook = default_balatro_playbooks().for_state(state)
            threshold_mapping = (
                playbook.strategy
                .get("decision_thresholds", {})
                .get("hand_action", {})
            )
            thresholds = HandActionThresholds.from_mapping(threshold_mapping)
            policy = LiveHandActionThresholdPolicy(thresholds)
            planner = D1LiveBlindClearPlanner(
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
            engine = LiveHandActionDecisionEngine(planner=planner, policy=policy)
            plans = engine.rank_plans(state)
            decision = policy.decide(state, plans)
    except Exception as error:
        print("Live-memory D1 hand-action validation -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse movement sent -> False")
        print("Mouse clicks sent -> False")
        print("Process writes/injection -> False")
        return 2

    print("Live-memory D1 hand-action validation -> PASS")
    print("Observation source -> live Balatro process memory")
    print(f"Phase -> {snapshot.phase}")
    print(f"Deck / stake -> {state.deck_name} / {state.stake_name}")
    print(f"Playbook -> {playbook.name} v{playbook.version}")
    print("Planner beam -> D1 diversity-aware")
    print("Process writes/injection -> False")
    print("Hidden RNG/deck traversal -> False")
    print("Mouse movement sent -> False")
    print("Mouse clicks sent -> False")
    print(f"Score / blind target -> {state.score} / {_target(state)}")
    print(f"Hands remaining -> {state.hands_remaining}")
    print(f"Discards remaining -> {state.discards_remaining}")
    print(f"Visible hand -> {len(state.hand)}")
    for index, card in enumerate(state.hand):
        print(f"  {index}: {_card_text(card)}")

    print("D1 thresholds:")
    for name, value in thresholds.as_dict().items():
        print(f"  {name} -> {value}")

    print(f"Planner candidates -> {len(plans)}")
    for index, plan in enumerate(plans, start=1):
        print(f"  {index}. {_plan_text(state, plan)}")

    print("Best Play -> " + _plan_text(state, decision.best_play))
    if decision.best_discard is None:
        print("Best Discard -> unavailable")
    else:
        print("Best Discard -> " + _plan_text(state, decision.best_discard))

    print(
        "Required discard clear-probability advantage -> "
        f"{decision.required_discard_clear_advantage:.6f}"
    )
    print(
        "Required discard progress advantage -> "
        f"{decision.required_discard_progress_advantage:.6f}"
    )
    if decision.clear_probability_delta is not None:
        print(
            "Discard - Play clear-probability delta -> "
            f"{decision.clear_probability_delta:.6f}"
        )
    if decision.progress_delta is not None:
        print(
            "Discard - Play progress delta -> "
            f"{decision.progress_delta:.6f}"
        )

    print(f"Recommended D1 action -> {decision.action.name}")
    print(f"Recommended indices -> {_indices(state, decision.action)}")
    print(f"D1 confidence -> {decision.confidence:.6f}")
    print("D1 rationale:")
    for reason in decision.rationale:
        print(f"  - {reason}")
    print(f"Planner nodes evaluated -> {planner.nodes_evaluated}")
    print("Integrated external action execution armed -> False for this validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
