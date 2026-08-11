from __future__ import annotations

import argparse

from games.balatro.live.synchronizer import BalatroLiveSynchronizer
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.playbook import BalatroPlaybookNotFound, default_balatro_playbooks

from .auto_blind_runner import _is_guaranteed, _print_plan
from .live_memory_hand_executor import (
    LiveMemoryHandExecutionError,
    LiveMemoryHandExecutor,
)
from .live_memory_observer import LiveMemoryBalatroObserver
from .live_search_policy import search_with_pace_fallback
from .production_observer import ProductionBalatroObserver
from .state_observer_factory import create_balatro_state_observer


def _raw_memory_observer(observer) -> LiveMemoryBalatroObserver:
    if isinstance(observer, ProductionBalatroObserver):
        return observer.observer
    if isinstance(observer, LiveMemoryBalatroObserver):
        return observer
    raise LiveMemoryHandExecutionError(
        "calibration-free hand execution requires live process-memory observation"
    )


def _execute_one(state, result, *, observer, snapshot, translator):
    plan = result.plan
    selected_ids = {id(card) for card in plan.action.cards}
    indices = tuple(
        index
        for index, card in enumerate(state.hand)
        if id(card) in selected_ids
    )

    executor = LiveMemoryHandExecutor(_raw_memory_observer(observer))
    executed_indices = executor.dispatch(plan.action, state, snapshot)
    if executed_indices != indices:
        raise RuntimeError("live-memory hand executor index mapping differs from planner mapping")

    print(f"Live card/control geometry guard -> PASS ({len(indices)} selected cards)")
    for index in indices:
        card = state.hand[index]
        geometry = ((snapshot.payload.get("hand") or {}).get("cards") or [])[index].get("ui") or {}
        print(
            f"  Live H{index}: {card.rank} / {card.suit} "
            f"T=({geometry.get('x')},{geometry.get('y')},"
            f"{geometry.get('w')},{geometry.get('h')})"
        )

    print("Execution targeting -> live Balatro UI geometry")
    print("Mouse calibration file used -> False")
    print("Screen card locator used -> False")
    print("Mouse input sent -> True")
    print("Waiting for live-memory checkpoint -> stable changed game state")
    persisted = BalatroLiveSynchronizer(
        observer,
        poll_interval=0.05,
        timeout=20.0,
    ).wait_for_change(
        snapshot,
        phases={"SELECTING_HAND", "ROUND_EVAL"},
        require_complete=True,
    )
    return persisted, translator.translate(persisted)


def _resolve_playbook_policy(args, state):
    playbook = default_balatro_playbooks().for_state(state)
    planner = dict((playbook.strategy or {}).get("planner") or {})

    if args.exact_only:
        args.min_clear_probability = None
    elif args.min_clear_probability is None:
        args.min_clear_probability = planner.get("min_clear_probability")

    if args.allow_consensus_discard is None:
        args.allow_consensus_discard = bool(
            planner.get("allow_consensus_discard", False)
        )
    if args.max_horizon is None:
        args.max_horizon = int(planner.get("max_horizon", 8))
    if args.max_search_nodes is None:
        args.max_search_nodes = int(planner.get("max_search_nodes", 5000))

    args.allow_pace_fallback = bool(planner.get("allow_pace_fallback", True))
    args.min_pace_ratio = float(planner.get("min_pace_ratio", 1.0))
    if args.min_pace_ratio <= 0:
        raise ValueError("playbook min_pace_ratio must be positive")

    return playbook


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Production blind runner: read Balatro directly from live process memory, "
            "load the deck/stake playbook, execute one guarded action at a time, "
            "checkpoint from live memory, and replan until the blind ends or policy blocks."
        )
    )
    parser.add_argument(
        "--observation-source",
        choices=("memory", "save"),
        default="memory",
        help="production default is live process memory; save is fallback/debug only",
    )
    parser.add_argument("--save", help="fallback save path; valid only with --observation-source save")
    parser.add_argument("--profile", default="1")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--exact-only", action="store_true")
    parser.add_argument(
        "--min-clear-probability",
        type=float,
        help="override the active playbook's scored-play execution threshold",
    )
    consensus = parser.add_mutually_exclusive_group()
    consensus.add_argument(
        "--allow-consensus-discard",
        dest="allow_consensus_discard",
        action="store_true",
        default=None,
        help="override the playbook to allow stable setup-discard consensus",
    )
    consensus.add_argument(
        "--no-consensus-discard",
        dest="allow_consensus_discard",
        action="store_false",
        help="override the playbook to disable setup-discard consensus",
    )
    parser.add_argument("--consensus-discard-agreement", type=int, default=3)
    parser.add_argument("--max-horizon", type=int, help="override playbook search horizon")
    parser.add_argument("--max-search-nodes", type=int, help="override playbook node budget")
    parser.add_argument("--max-actions", type=int, default=8)
    parser.add_argument("--exact-limit", type=int, default=1000)
    parser.add_argument("--child-exact-limit", type=int)
    args = parser.parse_args()

    if args.min_clear_probability is not None and not 0.0 <= args.min_clear_probability <= 1.0:
        parser.error("--min-clear-probability must be between 0 and 1")
    if args.consensus_discard_agreement < 2:
        parser.error("--consensus-discard-agreement must be at least 2")
    if args.max_horizon is not None and args.max_horizon < 1:
        parser.error("--max-horizon must be positive")
    if args.max_search_nodes is not None and args.max_search_nodes < 1:
        parser.error("--max-search-nodes must be positive")
    if args.max_actions < 1:
        parser.error("--max-actions must be positive")
    if args.exact_limit < 1:
        parser.error("--exact-limit must be positive")
    if args.child_exact_limit is not None and args.child_exact_limit < 1:
        parser.error("--child-exact-limit must be positive")
    if args.observation_source == "memory" and args.save is not None:
        parser.error("--save requires --observation-source save")
    if args.execute and args.observation_source != "memory":
        parser.error(
            "--execute requires --observation-source memory; save.jkr is fallback/debug only"
        )

    observer = create_balatro_state_observer(
        args.observation_source,
        save_path=args.save,
        profile=args.profile,
    )
    translator = DefaultBalatroStateTranslator()
    playbook = None
    actions_sent = 0

    try:
        while True:
            snapshot = observer.observe()
            if not snapshot.state_complete and args.observation_source == "memory":
                snapshot = BalatroLiveSynchronizer(
                    observer,
                    poll_interval=0.05,
                    timeout=10.0,
                ).wait_for_ready(
                    after_sequence=snapshot.sequence - 1,
                    require_complete=True,
                )
            state = translator.translate(snapshot)

            if playbook is None:
                try:
                    playbook = _resolve_playbook_policy(args, state)
                except (BalatroPlaybookNotFound, ValueError) as error:
                    parser.error(str(error))
                print("Observation source -> " + (
                    "live Balatro process memory"
                    if args.observation_source == "memory"
                    else "save.jkr fallback"
                ))
                print(f"Deck / Stake -> {state.deck_name} / {state.stake_name}")
                print(f"Playbook -> {playbook.name} v{playbook.version}")
                print(f"Planner max horizon -> {args.max_horizon}")
                print(f"Planner max nodes -> {args.max_search_nodes}")
                print(
                    "Scored-play minimum -> "
                    + (
                        f"{args.min_clear_probability:.6f}"
                        if args.min_clear_probability is not None
                        else "exact-guaranteed"
                    )
                )
                print(f"Consensus discard -> {args.allow_consensus_discard}")
                print(f"Pace fallback -> {args.allow_pace_fallback}")
                print(f"Minimum pace ratio -> {args.min_pace_ratio:.3f}")
                if args.observation_source == "memory":
                    print("Execution targeting -> live Balatro UI geometry")
                    print("Mouse calibration required -> False")

            print(f"Checkpoint sequence -> {snapshot.sequence}")
            print(f"Phase before -> {state.phase}")
            if state.phase == "ROUND_EVAL":
                print("Blind runner -> COMPLETE")
                print(f"Real actions sent -> {actions_sent}")
                print("Follow-up mouse input sent -> False")
                return 0
            if state.phase != "SELECTING_HAND":
                parser.error(f"Balatro is in {state.phase}, expected SELECTING_HAND")
            if not state.hand:
                parser.error("live state contains no current hand cards")
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
            print("Hidden RNG used -> False")
            print("Hidden draw order used -> False")

            try:
                decision = search_with_pace_fallback(state, args)
            except (RuntimeError, ValueError) as error:
                parser.error(str(error))

            result = decision.result
            if result is None:
                print("Execution guard -> BLOCKED")
                print("Reason -> no bounded search or pace fallback produced a usable plan")
                print("Mouse input sent -> False")
                return 0

            indices = _print_plan("Selected", state, result)
            accepted = decision.mode in {"threshold", "consensus-discard", "pace-play"}
            if decision.mode == "consensus-discard":
                print("Execution mode -> consensus-discard")
            elif decision.mode == "pace-play":
                print(
                    "Execution mode -> pace-play "
                    f"(minimum-ratio={args.min_pace_ratio:.3f})"
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
                print("Reason -> no search met clear, consensus-discard, or pace policy")
                print("Mouse input sent -> False")
                return 0
            if not args.execute:
                print("Mouse input sent -> False")
                print("Dry run -> live-memory adaptive search completed without executing")
                return 0
            if actions_sent >= args.max_actions:
                print("Execution guard -> BLOCKED")
                print(f"Reason -> reached --max-actions {args.max_actions}")
                print("Mouse input sent -> False")
                return 0

            latest = observer.observe()
            if latest.sequence != snapshot.sequence:
                print("Execution guard -> BLOCKED")
                print("Reason -> live Balatro state changed during search; replan from new checkpoint")
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
                    observer=observer,
                    snapshot=snapshot,
                    translator=translator,
                )
            except (RuntimeError, TimeoutError, ValueError) as error:
                parser.error(str(error))

            actions_sent += 1
            print(f"Checkpoint sequence after -> {persisted.sequence}")
            print(f"Phase after -> {persisted_state.phase}")
            print(f"Score after -> {persisted_state.score}")
            print(f"Hands after -> {persisted_state.hands_remaining}")
            print(f"Discards after -> {persisted_state.discards_remaining}")
            print(f"Hand cards after -> {len(persisted_state.hand)}")
            print(f"Owned Jokers after -> {len(persisted_state.jokers)}")
            print("Checkpoint source -> live Balatro process memory" if args.observation_source == "memory" else "Checkpoint source -> save.jkr fallback")
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

            print("Replan -> adaptive search from authoritative live checkpoint")
            print("---")
    finally:
        close = getattr(observer, "close", None)
        if callable(close):
            close()


if __name__ == "__main__":
    raise SystemExit(main())
