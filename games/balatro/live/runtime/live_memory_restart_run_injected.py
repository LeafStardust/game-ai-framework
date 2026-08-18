from __future__ import annotations

import argparse
from dataclasses import dataclass
from time import monotonic, sleep

from games.balatro.live.injected.bridge import InjectedBridgeError

from .live_memory_autonomous_step_injected import (
    LiveMemoryInjectedSingleStepRunner,
    _same_snapshot,
)
from .live_memory_observer import LiveMemoryBalatroObserver


DEFAULT_RESTART_TIMEOUT_SECONDS = 20.0
DEFAULT_RESTART_POLL_INTERVAL_SECONDS = 0.05
DEFAULT_RESTART_STABLE_CONFIRMATIONS = 6


class LiveRunRestartError(RuntimeError):
    pass


@dataclass(frozen=True)
class LiveRunRestartResult:
    before: object
    after: object
    bridge_status: dict[str, str]


def _identity(snapshot) -> tuple[str, str]:
    deck = str(snapshot.payload.get("deck") or "").upper()
    stake = str(snapshot.payload.get("stake") or "").upper()
    if not deck or not stake:
        raise LiveRunRestartError(
            "live snapshot does not expose deck/stake identity"
        )
    return deck, stake


def _validate_restart_source(snapshot) -> tuple[str, str]:
    if str(snapshot.phase) != "GAME_OVER":
        raise LiveRunRestartError(
            f"run restart requires GAME_OVER, observed {snapshot.phase}"
        )
    if not snapshot.state_complete:
        raise LiveRunRestartError("GAME_OVER snapshot is not complete")
    if bool(snapshot.payload.get("won")):
        raise LiveRunRestartError("won runs must not be restarted")
    return _identity(snapshot)


def _snapshot_diagnostic(snapshot) -> str:
    if snapshot is None:
        return "no post-command snapshot was observed"
    try:
        deck, stake = _identity(snapshot)
        identity = f"{deck}/{stake}"
    except LiveRunRestartError:
        identity = "UNAVAILABLE"
    return (
        f"last_phase={snapshot.phase}; "
        f"last_state_complete={bool(snapshot.state_complete)}; "
        f"last_sequence={snapshot.sequence}; "
        f"last_identity={identity}"
    )


def restart_fresh_unseeded_run(
    runner,
    deck: str,
    stake: str,
    *,
    timeout_seconds: float = DEFAULT_RESTART_TIMEOUT_SECONDS,
    poll_interval_seconds: float = DEFAULT_RESTART_POLL_INTERVAL_SECONDS,
    stable_confirmations: int = DEFAULT_RESTART_STABLE_CONFIRMATIONS,
) -> LiveRunRestartResult:
    """Restart one lost normal run and verify a sustained fresh checkpoint.

    The Lua bridge owns the destructive guard and mirrors Balatro's native held-R
    restart setup. Before setup begins, bridge revision 6+ also drains every native
    unlock confirmation currently stacked over the failed GAME_OVER screen by
    invoking Balatro's own ``continue_unlock`` callback. Python never writes process
    memory; it independently requires a sustained settled BLIND_SELECT checkpoint
    with the same deck/stake before returning.

    Unlock notifications are event-queue driven. A single or even two consecutive
    BLIND_SELECT observations can therefore occur before a late unlock/UI event
    finishes settling. Require several consecutive semantically equal fresh-run
    observations so the supervisor never reattaches in the middle of that tail and
    mistakes a resurfacing GAME_OVER/unlock frame for a new terminal attempt.
    """
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if poll_interval_seconds < 0:
        raise ValueError("poll_interval_seconds cannot be negative")
    if stable_confirmations < 2:
        raise ValueError("stable_confirmations must be at least 2")

    expected_deck = str(deck).upper()
    expected_stake = str(stake).upper()
    before = runner.observer.observe()
    observed_deck, observed_stake = _validate_restart_source(before)
    if (observed_deck, observed_stake) != (expected_deck, expected_stake):
        raise LiveRunRestartError(
            "restart identity mismatch before execution: expected "
            f"{expected_deck}/{expected_stake}, observed "
            f"{observed_deck}/{observed_stake}"
        )

    status = runner.bridge.status()
    if status.get("restart_run_callback") != "START_RUN_PRESENT":
        raise LiveRunRestartError(
            "first-party bridge does not report START_RUN_PRESENT"
        )
    if status.get("restart_unlock_drain") != "1":
        raise LiveRunRestartError(
            "first-party bridge does not advertise restart unlock-confirmation "
            "draining; close Balatro and reinstall/update the repository bridge"
        )

    runner.bridge.restart_run()

    deadline = monotonic() + timeout_seconds
    previous = None
    stable_count = 0
    last_observed = None
    while monotonic() < deadline:
        if poll_interval_seconds:
            sleep(poll_interval_seconds)
        current = runner.observer.observe()
        last_observed = current

        # The restart is asynchronous. Any incomplete frame, terminal frame,
        # unlock overlay tail, or identity transition resets the sustained-fresh
        # confirmation window instead of being accepted as attempt startup.
        if not current.state_complete or str(current.phase) != "BLIND_SELECT":
            previous = None
            stable_count = 0
            continue

        current_deck, current_stake = _identity(current)
        if (current_deck, current_stake) != (expected_deck, expected_stake):
            raise LiveRunRestartError(
                "restart reached BLIND_SELECT with changed deck/stake: expected "
                f"{expected_deck}/{expected_stake}, observed "
                f"{current_deck}/{current_stake}"
            )
        if current.sequence <= before.sequence:
            previous = None
            stable_count = 0
            continue

        if previous is not None and _same_snapshot(previous, current):
            stable_count += 1
        else:
            stable_count = 1

        previous = current
        if stable_count >= stable_confirmations:
            return LiveRunRestartResult(
                before=before,
                after=current,
                bridge_status=dict(status),
            )

    raise LiveRunRestartError(
        "restart command was accepted but no sustained settled same-deck/stake "
        "BLIND_SELECT checkpoint appeared before timeout; "
        + _snapshot_diagnostic(last_observed)
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate one guarded GAME_OVER -> fresh unseeded same deck/stake "
            "Balatro restart through the first-party injected bridge. Preview is "
            "read-only; --execute sends exactly one RESTART_RUN control command."
        )
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_RESTART_TIMEOUT_SECONDS,
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    try:
        with LiveMemoryBalatroObserver() as observer:
            runner = LiveMemoryInjectedSingleStepRunner(observer)
            before = observer.observe()
            deck, stake = _validate_restart_source(before)

            print("Live-memory native run restart -> READY")
            print(f"Phase before -> {before.phase}")
            print(f"Deck before -> {deck}")
            print(f"Stake before -> {stake}")
            print(f"Won before -> {bool(before.payload.get('won'))}")
            print("Restart target -> fresh unseeded same deck/stake run")
            print("Unlock confirmations -> drain all before restart")
            print("Process-memory writes -> False")
            print("Mouse input sent -> False")

            if not args.execute:
                print("Execution guard -> PREVIEW ONLY")
                print("Restart command sent -> False")
                return 0

            print(
                "WARNING -> --execute is armed: exactly one native RESTART_RUN "
                "control command may now be invoked"
            )
            result = restart_fresh_unseeded_run(
                runner,
                deck,
                stake,
                timeout_seconds=args.timeout,
            )
            print("Execution guard -> PASS")
            print("Restart command sent -> True")
            print(f"Bridge version -> {result.bridge_status.get('bridge', '?')}")
            print("Unlock confirmations drained -> True")
            print(f"Phase after -> {result.after.phase}")
            after_deck, after_stake = _identity(result.after)
            print(f"Deck after -> {after_deck}")
            print(f"Stake after -> {after_stake}")
            print(f"Checkpoint sequence after -> {result.after.sequence}")
            print("Restart postcondition -> PASS")
            return 0
    except (InjectedBridgeError, LiveRunRestartError, OSError, RuntimeError) as error:
        print("Live-memory native run restart -> BLOCKED")
        print(f"Reason -> {error}")
        print("Mouse input sent -> False")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
