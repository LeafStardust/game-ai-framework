from __future__ import annotations

import argparse
import time

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.hand_action_policy import (
    CLEAR_PATH,
    PACE_PLAY,
    PACE_RECOVERY,
    HandActionThresholds,
    LiveHandActionDecisionEngine,
    LiveHandActionPolicy,
)
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.playbook import default_balatro_playbooks

from .live_memory_action_dispatcher import LiveMemoryActionDispatcher
from .live_memory_observer import LiveMemoryBalatroObserver


_MODES = (CLEAR_PATH, PACE_PLAY, PACE_RECOVERY)
_ACTIONS = (PLAY_CARDS, DISCARD_CARDS)


def _parse_indices(value: str) -> tuple[int, ...]:
    parts = [part.strip() for part in str(value).split(",") if part.strip()]
    if not parts:
        raise ValueError("expected at least one hand index")
    try:
        indices = tuple(sorted(int(part) for part in parts))
    except ValueError as error:
        raise ValueError("hand indices must be comma-separated integers") from error
    if any(index < 0 for index in indices):
        raise ValueError("hand indices cannot be negative")
    if len(set(indices)) != len(indices):
        raise ValueError("hand indices cannot contain duplicates")
    return indices


def _indices(state, action) -> tuple[int, ...]:
    selected_ids = {id(card) for card in action.cards}
    selected_live_ids = {
        getattr(card, "live_id", None)
        for card in action.cards
        if getattr(card, "live_id", None) is not None
    }
    return tuple(
        index
        for index, card in enumerate(state.hand)
        if id(card) in selected_ids
        or (
            getattr(card, "live_id", None) is not None
            and getattr(card, "live_id", None) in selected_live_ids
        )
    )


def _state_fingerprint(state) -> tuple:
    hand = tuple(
        (
            getattr(card, "live_id", None),
            getattr(card, "rank", None),
            getattr(card, "suit", None),
            getattr(card, "enhancement", None),
            getattr(card, "edition", None),
            getattr(card, "seal", None),
        )
        for card in state.hand
    )
    return (
        getattr(state, "phase", None),
        int(getattr(state, "score", 0)),
        int(getattr(state, "hands_remaining", 0)),
        int(getattr(state, "discards_remaining", 0)),
        hand,
    )


def _decision_guard_errors(
    decision,
    state,
    *,
    expect_mode: str,
    expect_action: str,
    expect_indices: tuple[int, ...],
    min_clear_probability: float | None,
    min_pace_ratio: float | None,
) -> tuple[str, ...]:
    errors: list[str] = []
    actual_indices = _indices(state, decision.action)

    if decision.mode != expect_mode:
        errors.append(
            f"D1 mode changed: expected {expect_mode}, observed {decision.mode}"
        )
    if decision.action.name != expect_action:
        errors.append(
            f"D1 action changed: expected {expect_action}, observed {decision.action.name}"
        )
    if actual_indices != expect_indices:
        errors.append(
            f"D1 indices changed: expected {expect_indices}, observed {actual_indices}"
        )

    if decision.mode == CLEAR_PATH:
        clear_probability = float(decision.selected_plan.value.clear_probability)
        if min_clear_probability is None:
            errors.append("CLEAR_PATH execution requires an explicit minimum clear probability")
        elif clear_probability + 1e-12 < float(min_clear_probability):
            errors.append(
                "selected clear probability fell below the execution minimum: "
                f"minimum={min_clear_probability:.6f} observed={clear_probability:.6f}"
            )
        if not decision.selected_plan.exact and not decision.sampled_clear_path_confirmed:
            errors.append(
                "sampled CLEAR_PATH is not confirmed by the stronger same-horizon pass"
            )

    if decision.mode == PACE_PLAY:
        ratio = decision.selected_pace_ratio
        if min_pace_ratio is None:
            errors.append("PACE_PLAY execution requires an explicit minimum pace ratio")
        elif ratio is None or float(ratio) + 1e-12 < float(min_pace_ratio):
            observed = "unavailable" if ratio is None else f"{float(ratio):.6f}"
            errors.append(
                "selected pace ratio fell below the execution minimum: "
                f"minimum={min_pace_ratio:.6f} observed={observed}"
            )

    return tuple(errors)


def _wait_semantic_checkpoint(
    observer,
    translator,
    *,
    before_snapshot,
    before_state,
    action_name: str,
    timeout: float = 12.0,
    poll_interval: float = 0.05,
):
    deadline = time.monotonic() + max(0.0, float(timeout))
    last_snapshot = before_snapshot
    last_state = before_state

    while True:
        snapshot = observer.observe()
        state = translator.translate(snapshot)
        last_snapshot = snapshot
        last_state = state

        if snapshot.sequence > before_snapshot.sequence:
            if action_name == PLAY_CARDS:
                if state.phase == "ROUND_EVAL":
                    return snapshot, state
                if (
                    state.phase == "SELECTING_HAND"
                    and int(state.hands_remaining)
                    == int(before_state.hands_remaining) - 1
                    and bool(state.hand)
                ):
                    return snapshot, state
            elif action_name == DISCARD_CARDS:
                if (
                    state.phase == "SELECTING_HAND"
                    and int(state.discards_remaining)
                    == int(before_state.discards_remaining) - 1
                    and bool(state.hand)
                ):
                    return snapshot, state

        if time.monotonic() >= deadline:
            raise RuntimeError(
                "timed out waiting for authoritative D1 post-action checkpoint; "
                f"phase={last_state.phase} sequence={last_snapshot.sequence} "
                f"hands={last_state.hands_remaining} "
                f"discards={last_state.discards_remaining}"
            )
        if poll_interval:
            time.sleep(poll_interval)


def _target(state) -> int:
    blind = getattr(state, "blind", None)
    return int(getattr(blind, "requirement", 0)) if blind is not None else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Guarded one-action D1 live execution validation. Without --execute it "
            "only previews the current D1 decision. With --execute it sends real "
            "mouse clicks only when the recomputed mode/action/indices and explicit "
            "risk floor match the supplied expectations."
        )
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--expect-mode", choices=_MODES)
    parser.add_argument("--expect-action", choices=_ACTIONS)
    parser.add_argument("--expect-indices")
    parser.add_argument("--min-clear-probability", type=float)
    parser.add_argument("--min-pace-ratio", type=float)
    parser.add_argument("--max-horizon", type=int)
    parser.add_argument("--max-search-nodes", type=int)
    parser.add_argument("--exact-limit", type=int, default=128)
    parser.add_argument("--child-exact-limit", type=int, default=8)
    args = parser.parse_args()

    if args.execute and (
        args.expect_mode is None
        or args.expect_action is None
        or args.expect_indices is None
    ):
        parser.error(
            "--execute requires --expect-mode, --expect-action and --expect-indices"
        )
    if not args.execute and any(
        value is not None
        for value in (
            args.expect_mode,
            args.expect_action,
            args.expect_indices,
            args.min_clear_probability,
            args.min_pace_ratio,
        )
    ):
        parser.error("execution expectations are only valid with --execute")
    if args.min_clear_probability is not None and not 0.0 <= args.min_clear_probability <= 1.0:
        parser.error("--min-clear-probability must be between 0 and 1")
    if args.min_pace_ratio is not None and args.min_pace_ratio <= 0.0:
        parser.error("--min-pace-ratio must be positive")
    if args.max_horizon is not None and args.max_horizon < 1:
        parser.error("--max-horizon must be positive")
    if args.max_search_nodes is not None and args.max_search_nodes < 1:
        parser.error("--max-search-nodes must be positive")
    if args.exact_limit < 1 or args.child_exact_limit < 1:
        parser.error("exact combination limits must be positive")

    try:
        expected_indices = (
            _parse_indices(args.expect_indices)
            if args.expect_indices is not None
            else None
        )
    except ValueError as error:
        parser.error(str(error))

    translator = DefaultBalatroStateTranslator()
    with LiveMemoryBalatroObserver() as observer:
        snapshot = observer.observe()
        state = translator.translate(snapshot)
        if state.phase != "SELECTING_HAND":
            parser.error(
                f"D1 execution validation requires SELECTING_HAND, observed {state.phase}"
            )

        playbook = default_balatro_playbooks().for_state(state)
        thresholds = HandActionThresholds.from_mapping(
            playbook.strategy.get("decision_thresholds", {}).get("hand_action", {})
        )
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
        actual_indices = _indices(state, decision.action)

        print("Live-memory D1 guarded execution validation -> READY")
        print("Observation source -> live Balatro process memory")
        print(f"Deck / stake -> {state.deck_name} / {state.stake_name}")
        print(f"Playbook -> {playbook.name} v{playbook.version}")
        print(f"Score / blind target -> {state.score} / {_target(state)}")
        print(f"Hands / discards -> {state.hands_remaining} / {state.discards_remaining}")
        print(f"D1 mode -> {decision.mode}")
        print(f"Recommended action -> {decision.action.name}")
        print(f"Recommended indices -> {actual_indices}")
        print(f"Selected path exact -> {decision.selected_plan.exact}")
        print(
            "Selected clear probability -> "
            f"{decision.selected_plan.value.clear_probability:.6f}"
        )
        print(
            "Sampled clear-path confirmation -> "
            f"{decision.sampled_clear_path_confirmed}"
        )
        if decision.selected_pace_ratio is not None:
            print(f"Selected pace ratio -> {decision.selected_pace_ratio:.6f}x")
        print(f"D1 confidence -> {decision.confidence:.6f}")
        print("Process writes/injection -> False")

        if not args.execute:
            print("Execution guard -> PREVIEW ONLY")
            print("Mouse movement sent -> False")
            print("Mouse clicks sent -> False")
            return 0

        assert expected_indices is not None
        guard_errors = _decision_guard_errors(
            decision,
            state,
            expect_mode=args.expect_mode,
            expect_action=args.expect_action,
            expect_indices=expected_indices,
            min_clear_probability=args.min_clear_probability,
            min_pace_ratio=args.min_pace_ratio,
        )
        if guard_errors:
            print("Execution guard -> BLOCKED")
            for error in guard_errors:
                print(f"Reason -> {error}")
            print("Mouse movement sent -> False")
            print("Mouse clicks sent -> False")
            return 0

        latest_snapshot = observer.observe()
        latest_state = translator.translate(latest_snapshot)
        if (
            latest_snapshot.sequence != snapshot.sequence
            or _state_fingerprint(latest_state) != _state_fingerprint(state)
        ):
            print("Execution guard -> BLOCKED")
            print("Reason -> live hand state changed during planning; re-run from the new checkpoint")
            print("Mouse movement sent -> False")
            print("Mouse clicks sent -> False")
            return 0

        print("Execution guard -> PASS")
        print("WARNING -> --execute is armed: real mouse movement/clicks will now be sent")
        print("Execution scope -> exactly one D1 Play/Discard action")

        with LiveMemoryActionDispatcher(observer=observer) as dispatcher:
            result = dispatcher.dispatch(
                decision.action,
                state=latest_state,
                snapshot=latest_snapshot,
            )

        checkpoint_snapshot, checkpoint_state = _wait_semantic_checkpoint(
            observer,
            translator,
            before_snapshot=latest_snapshot,
            before_state=latest_state,
            action_name=decision.action.name,
        )

        print("Mouse input sent -> True")
        print(f"Executed indices -> {result.details}")
        print(f"Checkpoint sequence -> {checkpoint_snapshot.sequence}")
        print(f"Phase after -> {checkpoint_state.phase}")
        print(f"Score after -> {checkpoint_state.score}")
        print(f"Hands after -> {checkpoint_state.hands_remaining}")
        print(f"Discards after -> {checkpoint_state.discards_remaining}")
        print(f"Visible hand after -> {len(checkpoint_state.hand)}")
        print("Follow-up D1 action executed -> False")
        print("Next step -> re-run the read-only D1 validator from this authoritative checkpoint")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
