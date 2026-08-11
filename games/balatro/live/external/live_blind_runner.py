from __future__ import annotations

import argparse
from pathlib import Path

from games.balatro.live.synchronizer import BalatroLiveSynchronizer
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.playbook import BalatroPlaybookNotFound, default_balatro_playbooks

from .auto_blind_runner import (
    DEFAULT_LAYOUT,
    _is_guaranteed,
    _print_plan,
    _search,
)
from .expected_card_locator import locate_card_faces_expected_count
from .hand_mouse import ExternalHandMouseExecutor, HandMouseLayout
from .mouse import BalatroMouseController
from .state_observer_factory import create_balatro_state_observer


def _execute_one(state, result, *, layout, observer, snapshot, translator):
    plan = result.plan
    selected_ids = {id(card) for card in plan.action.cards}
    indices = tuple(
        index
        for index, card in enumerate(state.hand)
        if id(card) in selected_ids
    )

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
        print(f"Screen/live-state exact-count guard -> PASS ({len(locations)})")
        for index in indices:
            location = locations[index]
            card = state.hand[index]
            print(
                f"  Screen {index}: {card.rank} / {card.suit} "
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

    return playbook


def _load_execution_layout(execute: bool, path: str):
    """Load mouse calibration only when real input is armed."""
    if not execute:
        return None
    layout = HandMouseLayout.load(Path(path))
    layout.point_for("play-hand")
    layout.point_for("discard")
    return layout


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
    parser.add_argument("--layout", default=DEFAULT_LAYOUT)
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

    try:
        layout = _load_execution_layout(args.execute, args.layout)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))

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
                except BalatroPlaybookNotFound as error:
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
                print("Execution mode -> consensus-discard")
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
                print("Reason -> no adaptive search met the active playbook execution policy")
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

            if layout is None:
                parser.error("execution layout is unavailable while --execute is armed")

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
