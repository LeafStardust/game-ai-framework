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


DEFAULT_RESTART_TIMEOUT_SECONDS = 60.0
DEFAULT_RESTART_POLL_INTERVAL_SECONDS = 0.05
DEFAULT_RESTART_STABLE_CONFIRMATIONS = 6
DEFAULT_RESTART_RETRY_INTERVAL_SECONDS = 1.0


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
    retry_interval_seconds: float = DEFAULT_RESTART_RETRY_INTERVAL_SECONDS,
) -> LiveRunRestartResult:
    """Restart one lost normal run and verify a sustained fresh checkpoint.

    Loss restart is intentionally resilient. Unlock notifications and GAME_OVER UI
    teardown are asynchronous, so a RESTART_RUN command can be temporarily rejected
    while Balatro is still exposing the same authoritative lost GAME_OVER state.
    While that source remains valid, retry the guarded native restart command instead
    of treating a transient bridge/UI rejection as an agent-fatal condition.

    Once Balatro leaves GAME_OVER, never issue another destructive restart command.
    Only observe until a sustained same-deck/stake BLIND_SELECT checkpoint appears.
    This prevents a command whose result was merely delayed from restarting the new
    run a second time. Python never writes process memory.
    """
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if poll_interval_seconds < 0:
        raise ValueError("poll_interval_seconds cannot be negative")
    if stable_confirmations < 2:
        raise ValueError("stable_confirmations must be at least 2")
    if retry_interval_seconds <= 0:
        raise ValueError("retry_interval_seconds must be positive")

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

    deadline = monotonic() + timeout_seconds
    next_restart_attempt = monotonic()
    command_accepted = False
    last_command_error: Exception | None = None
    previous = None
    stable_count = 0
    last_observed = before

    while monotonic() < deadline:
        current = runner.observer.observe()
        last_observed = current
        phase = str(current.phase)

        if current.state_complete and phase == "BLIND_SELECT":
            current_deck, current_stake = _identity(current)
            if (current_deck, current_stake) != (expected_deck, expected_stake):
                raise LiveRunRestartError(
                    "restart reached BLIND_SELECT with changed deck/stake: expected "
                    f"{expected_deck}/{expected_stake}, observed "
                    f"{current_deck}/{current_stake}"
                )
            if current.sequence > before.sequence:
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
            else:
                previous = None
                stable_count = 0
        else:
            previous = None
            stable_count = 0

        # Retry only while the authoritative state still says this is the same
        # lost GAME_OVER run. As soon as the first restart starts transitioning,
        # observation-only verification takes over.
        now = monotonic()
        if (
            current.state_complete
            and phase == "GAME_OVER"
            and not bool(current.payload.get("won"))
            and now >= next_restart_attempt
        ):
            current_deck, current_stake = _identity(current)
            if (current_deck, current_stake) != (expected_deck, expected_stake):
                raise LiveRunRestartError(
                    "restart source changed deck/stake while retrying: expected "
                    f"{expected_deck}/{expected_stake}, observed "
                    f"{current_deck}/{current_stake}"
                )
            try:
                runner.bridge.restart_run()
                command_accepted = True
                last_command_error = None
            except InjectedBridgeError as error:
                # Unlock overlays/event queues can make the native callback
                # temporarily unavailable. Keep the supervisor alive and retry
                # from the still-authoritative lost GAME_OVER checkpoint.
                last_command_error = error
            next_restart_attempt = now + retry_interval_seconds

        if poll_interval_seconds:
            sleep(poll_interval_seconds)

    detail = _snapshot_diagnostic(last_observed)
    if last_command_error is not None and not command_accepted:
        raise LiveRunRestartError(
            "restart remained transiently blocked while the lost GAME_OVER run "
            f"was still active; last_bridge_error={last_command_error}; {detail}"
        )
    raise LiveRunRestartError(
        "restart did not reach a sustained settled same-deck/stake BLIND_SELECT "
        f"checkpoint before timeout; command_accepted={command_accepted}; {detail}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate one guarded GAME_OVER -> fresh unseeded same deck/stake "
            "Balatro restart through the first-party injected bridge. Preview is "
            "read-only; --execute sends guarded RESTART_RUN commands only while "
            "the same lost GAME_OVER source remains authoritative."
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
            print("Transient restart rejection -> guarded retry while GAME_OVER remains")
            print("Process-memory writes -> False")
            print("Mouse input sent -> False")

            if not args.execute:
                print("Execution guard -> PREVIEW ONLY")
                print("Restart command sent -> False")
                return 0

            print(
                "WARNING -> --execute is armed: guarded native RESTART_RUN retries "
                "may occur only while the same lost GAME_OVER source remains"
            )
            result = restart_fresh_unseeded_run(
                runner,
                deck,
                stake,
                timeout_seconds=args.timeout,
            )
            print("Execution guard -> PASS")
            print("Restart completed -> True")
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
