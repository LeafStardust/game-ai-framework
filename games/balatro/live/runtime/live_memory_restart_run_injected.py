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
) -> LiveRunRestartResult:
    """Restart one lost normal run and verify the new public checkpoint.

    The Lua bridge owns the destructive guard and mirrors Balatro's native held-R
    restart setup. Python never writes process memory; it independently requires a
    settled BLIND_SELECT checkpoint with the same deck/stake before returning.

    Balatro's native restart is asynchronous and includes wipe/setup animation, so
    the verifier deliberately allows the same 20-second settling envelope used by
    older live transition synchronization instead of treating a five-second visual
    transition as a control-path failure.
    """
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if poll_interval_seconds < 0:
        raise ValueError("poll_interval_seconds cannot be negative")

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

    runner.bridge.restart_run()

    deadline = monotonic() + timeout_seconds
    previous = None
    last_observed = None
    while monotonic() < deadline:
        if poll_interval_seconds:
            sleep(poll_interval_seconds)
        current = runner.observer.observe()
        last_observed = current

        # The restart is asynchronous. Ignore incomplete/transient wipe frames and
        # require two consecutive semantically equal authoritative snapshots.
        if not current.state_complete:
            previous = None
            continue
        if str(current.phase) != "BLIND_SELECT":
            previous = current
            continue

        current_deck, current_stake = _identity(current)
        if (current_deck, current_stake) != (expected_deck, expected_stake):
            raise LiveRunRestartError(
                "restart reached BLIND_SELECT with changed deck/stake: expected "
                f"{expected_deck}/{expected_stake}, observed "
                f"{current_deck}/{current_stake}"
            )
        if current.sequence <= before.sequence:
            previous = current
            continue

        if previous is not None and _same_snapshot(previous, current):
            return LiveRunRestartResult(
                before=before,
                after=current,
                bridge_status=dict(status),
            )
        previous = current

    raise LiveRunRestartError(
        "restart command was accepted but no settled same-deck/stake "
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
