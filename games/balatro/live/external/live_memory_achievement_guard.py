from __future__ import annotations

import argparse

from games.balatro.live.injected.bridge import (
    FirstPartyBalatroBridge,
    InjectedBridgeError,
    InjectedBridgeProtocolError,
)


ACHIEVEMENT_STATUS_FIELD = "achievement_gate"


def achievement_gate_state(
    value: str | None,
) -> tuple[str, bool | None]:
    state = str(value or "MISSING")
    if state in {"UNSET", "ENABLED"}:
        return state, False
    if state == "DISABLED":
        return state, True
    return state, None


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read Balatro's achievement-disable gate through the first-party "
            "in-process bridge. This validation does not mutate gameplay state."
        )
    )
    parser.parse_args()

    bridge = FirstPartyBalatroBridge()
    try:
        status = bridge.status()
    except InjectedBridgeError as error:
        print("Live Balatro achievement-gate validation -> FAIL")
        print("Observation source -> first-party in-process bridge status")
        print("Gameplay state mutation -> False")
        print("Mouse input sent -> False")
        print(f"Bridge status error -> {error}")
        print(
            "Result -> FAIL CLOSED: bridge status could not be read; make sure "
            "the current bridge asset is installed and Balatro was restarted"
        )
        return 1

    bridge_version = status.get("bridge")
    raw_gate = status.get(ACHIEVEMENT_STATUS_FIELD)
    state, disabled = achievement_gate_state(raw_gate)

    print("Live Balatro achievement-gate validation -> READY")
    print("Observation source -> first-party in-process bridge status")
    print("Gameplay state mutation -> False")
    print("Mouse input sent -> False")
    print("Status command sent -> True")
    print(f"Bridge version -> {bridge_version or 'MISSING'}")
    print(f"G.F_NO_ACHIEVEMENTS state -> {state}")

    if bridge_version != "1":
        print("Steam achievement gate -> UNKNOWN")
        print(
            "Result -> FAIL CLOSED: unexpected or missing bridge version"
        )
        return 1

    if disabled is True:
        print("Steam achievement gate -> BLOCKED BY BALATRO FLAG")
        print(
            "Result -> FAIL: do not use this execution backend until the "
            "achievement-disable source is identified"
        )
        return 1

    if disabled is None:
        print("Steam achievement gate -> UNKNOWN")
        print(
            "Result -> FAIL CLOSED: unexpected or unavailable flag representation"
        )
        return 1

    print("Steam achievement gate -> NOT DISABLED")
    print(
        "Result -> PASS for the in-game achievement gate; an actual Steam "
        "achievement unlock still requires live validation"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
