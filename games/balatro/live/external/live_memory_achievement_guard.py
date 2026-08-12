from __future__ import annotations

import argparse

from games.balatro.live.external.luajit_memory import LuaValue
from games.balatro.live.external.live_memory_observer import (
    LiveMemoryBalatroObserver,
)


ACHIEVEMENT_FLAG = "F_NO_ACHIEVEMENTS"


def achievement_gate_state(
    value: LuaValue | None,
) -> tuple[str, bool | None]:
    if value is None or value.kind == "nil":
        return "UNSET", False
    if value.kind == "boolean":
        disabled = bool(value.value)
        return ("DISABLED" if disabled else "ENABLED"), disabled
    return f"UNEXPECTED:{value.kind}", None


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read Balatro's achievement-disable gate directly from live memory. "
            "This validation is strictly read-only and never changes the flag."
        )
    )
    parser.parse_args()

    with LiveMemoryBalatroObserver() as observer:
        _, _, root = observer._root()
        value = root.get(ACHIEVEMENT_FLAG)
        state, disabled = achievement_gate_state(value)

        print("Live Balatro achievement-gate validation -> READY")
        print("Observation source -> live Balatro process memory")
        print("Process writes/injection -> False")
        print("Mouse input sent -> False")
        print(f"G.{ACHIEVEMENT_FLAG} state -> {state}")

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
                "Result -> FAIL CLOSED: unexpected flag representation"
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
