from __future__ import annotations

import argparse

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.hand_action_policy import (
    HandActionThresholds,
    LiveHandActionDecisionEngine,
    LiveHandActionPolicy,
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
        f"exact={plan.exact} horizon={plan.horizon}"
    )


def _target(state) -> int:
    blind = getattr(state, "blind", None)
    return int(getattr(blind, "requirement", 0)) if blind is not None else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only D1 live validation. Adaptively searches for a blind-clear path; "
            "only when none reaches the D1 floor does it fall back to remaining blind "
            "score divided by remaining hands. Sends no mouse input."
        )
    )
    parser.add_argument("--max-horizon", type=int)
    parser.add_argument("--max-search-nodes", type=int)
    parser.add_argument("--exact-limit", type=int, default=128)
    parser.add_argument("--child-exact-limit", type=int, default=8)
    args = parser.parse_args()

    for name in ("max_horizon", "max_search_nodes"):
        value = getattr(args, name)
        if value is not None and value < 1:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if args.exact_limit < 1:
        parser.error("--exact-limit must be positive")
    if args.child_exact_limit < 1:
        parser.error("--child-exact-limit must be positive")

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
            planner_config = playbook.strategy.get("planner", {})
            max_horizon = (
                args.max_horizon
                if args.max_horizon is not None
                else int(planner_config.get("max_horizon", 8))
            )
            max_search_nodes = (
                args.max_search_nodes
                if args.max_search_nodes is not None
                else int(planner_config.get("max_search_nodes", 5000))
            )

            policy = LiveHandActionPolicy(thresholds)
            engine = LiveHandActionDecisionEngine(
                policy=policy,
                max_horizon=max_horizon,
                max_search_nodes=max_search_nodes,
                exact_limit=args.exact_limit,
                child_exact_limit=args.child_exact_limit,
            )
            decision = engine.decide(state)
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
    print("Decision hierarchy -> CLEAR_PATH -> PACE_PLAY -> PACE_RECOVERY")
    print("Clear-path search -> adaptive bounded public-state expectimax")
    print("Pace fallback beam -> D1 diversity-aware")
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

    print(f"Adaptive clear-path attempts -> {len(decision.search_attempts)}")
    for index, attempt in enumerate(decision.search_attempts, start=1):
        if attempt.budget_exceeded:
            print(
                f"  {index}. horizon={attempt.horizon} samples={attempt.samples} "
                f"beam={attempt.play_width}+{attempt.discard_width} "
                f"nodes={attempt.nodes_evaluated}/{attempt.max_nodes} BUDGET_EXCEEDED"
            )
        else:
            print(
                f"  {index}. horizon={attempt.horizon} samples={attempt.samples} "
                f"beam={attempt.play_width}+{attempt.discard_width} "
                f"nodes={attempt.nodes_evaluated}/{attempt.max_nodes} "
                f"best={attempt.best_action} "
                f"clear={attempt.best_clear_probability:.6f} "
                f"expected={attempt.best_expected_score:.3f}"
            )

    print(f"Decision-mode candidates -> {len(decision.plans)}")
    for index, plan in enumerate(decision.plans, start=1):
        print(f"  {index}. {_plan_text(state, plan)}")

    print("Best planner Play -> " + _plan_text(state, decision.best_play))
    if decision.best_discard is None:
        print("Best planner Discard -> unavailable")
    else:
        print("Best planner Discard -> " + _plan_text(state, decision.best_discard))

    print(
        "Pace target -> "
        f"({_target(state)} - {state.score}) / {state.hands_remaining} = "
        f"{decision.pace_target:.3f} chips on the next hand"
    )
    print(
        "Best immediate Play score / pace ratio -> "
        f"{decision.best_play_immediate_score:.3f} / "
        f"{decision.best_play_pace_ratio:.6f}x"
    )
    print(f"Clear-path candidates above floor -> {decision.clear_path_candidates}")
    print(f"Setup-discard deep-search consensus -> {decision.setup_discard_consensus}")
    print(f"D1 mode -> {decision.mode}")
    print(f"Recommended D1 action -> {decision.action.name}")
    print(f"Recommended indices -> {_indices(state, decision.action)}")
    if decision.selected_immediate_score is not None:
        print(f"Selected immediate score -> {decision.selected_immediate_score:.3f}")
    if decision.selected_pace_ratio is not None:
        print(f"Selected pace ratio -> {decision.selected_pace_ratio:.6f}x")
    if decision.selected_fallback_value is not None:
        print(f"Selected pace-recovery value -> {decision.selected_fallback_value:.3f}")
    print(f"D1 confidence -> {decision.confidence:.6f}")
    print("D1 rationale:")
    for reason in decision.rationale:
        print(f"  - {reason}")
    print("Integrated external action execution armed -> False for this validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
