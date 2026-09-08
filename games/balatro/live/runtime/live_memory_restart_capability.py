from __future__ import annotations

from games.balatro.live.injected.bridge import (
    FirstPartyBalatroBridge,
    InjectedBridgeError,
)

from .live_memory_observer import LiveMemoryBalatroObserver


RESTART_CALLBACK_UNREPORTED = "UNREPORTED"


def restart_callback_state(status: dict[str, str]) -> str:
    return str(status.get("restart_run_callback") or RESTART_CALLBACK_UNREPORTED)


def main() -> int:
    try:
        with LiveMemoryBalatroObserver() as observer:
            snapshot = observer.observe()
            bridge = FirstPartyBalatroBridge()
            status = bridge.status()
    except (InjectedBridgeError, RuntimeError, ValueError, OSError) as error:
        print("Live restart capability -> FAIL")
        print(f"Reason -> {error}")
        print("Restart command sent -> False")
        print("Gameplay command sent -> False")
        return 2

    callback = restart_callback_state(status)
    print("Live restart capability -> READY")
    print(f"Phase -> {snapshot.phase}")
    print(f"Bridge version -> {status.get('bridge', 'MISSING')}")
    print(f"Restart callback probe -> {callback}")
    if callback == "START_RUN_PRESENT":
        print(
            "Probe meaning -> G.FUNCS.start_run exists; calling contract and "
            "restart semantics are NOT yet validated"
        )
    elif callback == RESTART_CALLBACK_UNREPORTED:
        print(
            "Probe meaning -> installed bridge does not report the new capability "
            "field; reinstall the current first-party bridge and restart Balatro"
        )
    else:
        print(
            "Probe meaning -> reported callback-presence state only; no restart "
            "semantics were exercised"
        )
    print("Status command sent -> True")
    print("Restart command sent -> False")
    print("Gameplay command sent -> False")
    print("Observation process writes -> False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
