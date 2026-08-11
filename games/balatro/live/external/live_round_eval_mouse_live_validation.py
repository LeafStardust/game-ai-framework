from __future__ import annotations

import argparse

from games.balatro.live.synchronizer import BalatroLiveSynchronizer

from .live_memory_observer import LiveMemoryBalatroObserver
from .live_round_eval_mouse import (
    LiveMemoryRoundEvalMouseExecutor,
    LiveRoundEvalMouseError,
)
from .mouse import BalatroMouseController


def _fmt_geometry(value: dict[str, float]) -> str:
    return " ".join(
        f"{name}={value[name]:.6f}"
        for name in ("x", "y", "w", "h", "r", "scale")
        if name in value
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or execute exactly one Balatro Cash Out click using live "
            "ROUND_EVAL UI geometry, then verify the transition to SHOP."
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="arm normal mouse input and click the live Cash Out center exactly once",
    )
    args = parser.parse_args()

    try:
        with LiveMemoryBalatroObserver() as observer:
            mouse = BalatroMouseController(armed=args.execute)
            executor = LiveMemoryRoundEvalMouseExecutor(
                observer=observer,
                mouse=mouse,
            )

            snapshot, target, window = executor.preview()
            rect = window.client_rect
            print("Live ROUND_EVAL mouse validation -> READY")
            print("Observation source -> live Balatro process memory")
            print(f"Phase before -> {snapshot.phase}")
            print("Process writes/injection -> False")
            print("Hidden RNG/deck traversal -> False")
            print("Target source -> G.CONTROLLER.snap_cursor_to.node")
            print(f"Node address -> 0x{target.node_address:x}")
            print(f"button -> {target.button!r}")
            print(f"id -> {target.control_id!r}")
            print(f"Geometry source -> {target.geometry_source}")
            print(f"Geometry -> {_fmt_geometry(target.geometry)}")
            print(
                "Balatro client rect -> "
                f"left={rect.left} top={rect.top} width={rect.width} height={rect.height}"
            )
            print(
                "Live Cash Out center -> "
                f"x={target.screen_center.x} y={target.screen_center.y}"
            )

            if not args.execute:
                print("Mouse input sent -> False")
                print(
                    "Re-run with --execute to send exactly one normal mouse click "
                    "to this live-derived Cash Out control."
                )
                return 0

            before, clicked_target = executor.dispatch()
            print("Mouse input sent -> True")
            print(
                "Clicked live Cash Out center -> "
                f"x={clicked_target.screen_center.x} "
                f"y={clicked_target.screen_center.y}"
            )
            print("Waiting for live checkpoint -> SHOP")

            after = BalatroLiveSynchronizer(
                observer,
                poll_interval=0.05,
                timeout=15.0,
            ).wait_for_change(
                before,
                phases={"SHOP"},
                require_complete=False,
            )
    except (OSError, RuntimeError, TimeoutError, ValueError, LiveRoundEvalMouseError) as error:
        print("Live ROUND_EVAL mouse validation -> FAIL")
        print(f"Reason -> {error}")
        return 2

    print(f"Phase after -> {after.phase}")
    print(f"State complete after -> {after.state_complete}")
    print(f"Money after -> {after.payload.get('money')}")
    print("ROUND_EVAL -> SHOP checkpoint verified -> True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
