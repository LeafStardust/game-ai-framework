from __future__ import annotations

import argparse

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.live.hand_action_policy import (
    CLEAR_PATH,
    PACE_PLAY,
    PACE_RECOVERY,
    HandActionThresholds,
    LiveHandActionDecisionEngine,
    LiveHandActionPolicy,
)
from games.balatro.live.injected import (
    FirstPartyBalatroBridge,
    InjectedBridgeError,
    LiveMemoryInjectedHandDispatcher,
)
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.playbook import default_balatro_playbooks

from .live_memory_hand_action_execute_validation import (
    _decision_guard_errors,
    _indices,
    _parse_indices,
    _state_fingerprint,
    _target,
)
from .live_memory_observer import LiveMemoryBalatroObserver


_MODES = (CLEAR_PATH, PACE_PLAY, PACE_RECOVERY)
_ACTIONS = (PLAY_CARDS, DISCARD_CARDS)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Guarded one-action D1 validation using the game-ai-framework "
            "first-party in-process Balatro bridge. Preview mode is read-only. "
            "--execute submits exactly one Play/Discard command and sends no "
            "mouse input."
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
            "--execute requires --expect-mode, --expect-action "
            "and --expect-indices"
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
        parser.error(
            "execution expectations are only valid with --execute"
        )
    if (
        args.min_clear_probability is not None
        and not 0.0 <= args.min_clear_probability <= 1.0
    ):
        parser.error(
            "--min-clear-probability must be between 0 and 1"
        )
    if (
        args.min_pace_ratio is not None
        and args.min_pace_ratio <= 0.0
    ):
        parser.error("--min-pace-ratio must be positive")
    if args.max_horizon is not None and args.max_horizon < 1:
        parser.error("--max-horizon must be positive")
    if (
        args.max_search_nodes is not None
        and args.max_search_nodes < 1
    ):
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
                "D1 injected execution validation requires "
                f"SELECTING_HAND, observed {state.phase}"
            )

        playbook = default_balatro_playbooks().for_state(state)
        thresholds = HandActionThresholds.from_mapping(
            playbook.strategy.get(
                "decision_thresholds",
                {},
            ).get(
                "hand_action",
                {},
            )
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
            else int(
                planner_config.get(
                    "max_search_nodes",
                    5000,
                )
            )
        )
        engine = LiveHandActionDecisionEngine(
            policy=LiveHandActionPolicy(thresholds),
            max_horizon=max_horizon,
            max_search_nodes=max_search_nodes,
            exact_limit=args.exact_limit,
            child_exact_limit=args.child_exact_limit,
        )
        decision = engine.decide(state)
        actual_indices = _indices(state, decision.action)

        print(
            "Live-memory D1 first-party injected validation -> READY"
        )
        print("Observation source -> live Balatro process memory")
        print(
            "Execution backend -> "
            "game-ai-framework injected Lua bridge"
        )
        print("Runtime loader -> none (fused LÖVE archive)")
        print("Lovely required -> False")
        print("Steamodded required -> False")
        print("BalatroBot required -> False")
        print("Mouse calibration required -> False")
        print(f"Deck / stake -> {state.deck_name} / {state.stake_name}")
        print(f"Playbook -> {playbook.name} v{playbook.version}")
        print(
            f"Score / blind target -> "
            f"{state.score} / {_target(state)}"
        )
        print(
            f"Hands / discards -> "
            f"{state.hands_remaining} / "
            f"{state.discards_remaining}"
        )
        print(f"D1 mode -> {decision.mode}")
        print(f"Recommended action -> {decision.action.name}")
        print(f"Recommended indices -> {actual_indices}")
        print(
            f"Selected path exact -> "
            f"{decision.selected_plan.exact}"
        )
        print(
            "Selected clear probability -> "
            f"{decision.selected_plan.value.clear_probability:.6f}"
        )
        print(
            "Sampled clear-path confirmation -> "
            f"{decision.sampled_clear_path_confirmed}"
        )
        if decision.selected_pace_ratio is not None:
            print(
                f"Selected pace ratio -> "
                f"{decision.selected_pace_ratio:.6f}x"
            )
        print(f"D1 confidence -> {decision.confidence:.6f}")
        print("Observation process writes -> False")

        if not args.execute:
            print("Execution guard -> PREVIEW ONLY")
            print("Injected bridge command sent -> False")
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
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        latest_snapshot = observer.observe()
        latest_state = translator.translate(latest_snapshot)
        if (
            latest_snapshot.sequence != snapshot.sequence
            or _state_fingerprint(latest_state)
            != _state_fingerprint(state)
        ):
            print("Execution guard -> BLOCKED")
            print(
                "Reason -> live hand state changed during planning; "
                "re-run from the new checkpoint"
            )
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        bridge = FirstPartyBalatroBridge()
        try:
            bridge.ping()
        except InjectedBridgeError as error:
            print("Execution guard -> BLOCKED")
            print(
                "Reason -> first-party injected bridge unavailable: "
                f"{error}"
            )
            print(
                "Setup -> "
                "py -m games.balatro.live.injected.install "
                "then restart Balatro"
            )
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        print("Execution guard -> PASS")
        print(
            "WARNING -> --execute is armed: one real in-process "
            "Balatro Play/Discard action will now be invoked"
        )
        print(
            "Execution scope -> exactly one D1 Play/Discard action"
        )
        print("Mouse input sent -> False")

        try:
            result = LiveMemoryInjectedHandDispatcher(
                observer,
                bridge=bridge,
            ).dispatch(
                decision.action,
                state=latest_state,
                snapshot=latest_snapshot,
            )
        except (InjectedBridgeError, RuntimeError) as error:
            print("Injected execution -> FAILED")
            print(f"Reason -> {error}")
            print("Follow-up D1 action executed -> False")
            return 1

        checkpoint_snapshot = result.after
        checkpoint_state = translator.translate(
            checkpoint_snapshot
        )

        print("Injected bridge command sent -> True")
        print(f"Executed indices -> {result.details}")
        print(
            f"Checkpoint sequence -> "
            f"{checkpoint_snapshot.sequence}"
        )
        print(f"Phase after -> {checkpoint_state.phase}")
        print(f"Score after -> {checkpoint_state.score}")
        print(
            f"Hands after -> "
            f"{checkpoint_state.hands_remaining}"
        )
        print(
            f"Discards after -> "
            f"{checkpoint_state.discards_remaining}"
        )
        print(
            f"Visible hand after -> "
            f"{len(checkpoint_state.hand)}"
        )
        print("Follow-up D1 action executed -> False")
        print(
            "Next step -> re-run the read-only D1 validator "
            "from this authoritative checkpoint"
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
