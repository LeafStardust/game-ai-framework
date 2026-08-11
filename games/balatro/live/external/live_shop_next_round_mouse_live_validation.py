from __future__ import annotations

import argparse

from games.balatro.live.synchronizer import BalatroLiveSynchronizer

from .live_memory_observer import LiveMemoryBalatroObserver
from .live_shop_next_round_mouse import (
    LiveMemoryShopNextRoundMouseExecutor,
    LiveShopNextRoundMouseError,
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
            "Preview or execute exactly one Balatro Next Round click using live "
            "SHOP UI geometry, then verify the transition to BLIND_SELECT."
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="arm normal mouse input and click the live Next Round center exactly once",
    )
    args = parser.parse_args()

    try:
        with LiveMemoryBalatroObserver() as observer:
            mouse = BalatroMouseController(armed=args.execute)
            executor = LiveMemoryShopNextRoundMouseExecutor(
                observer=observer,
                mouse=mouse,
            )

            snapshot, target, window = executor.preview()
            rect = window.client_rect
            print("Live SHOP Next Round mouse validation -> READY")
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
                "Live Next Round center -> "
                f"x={target.screen_center.x} y={target.screen_center.y}"
            )

            if not args.execute:
                print("Mouse input sent -> False")
                print(
                    "Re-run with --execute to send exactly one normal mouse click "
                    "to this live-derived Next Round control."
                )
                return 0

            before, clicked_target = executor.dispatch()
            print("Mouse input sent -> True")
            print(
                "Clicked live Next Round center -> "
                f"x={clicked_target.screen_center.x} "
                f"y={clicked_target.screen_center.y}"
            )
            print("Waiting for live checkpoint -> BLIND_SELECT")

            after = BalatroLiveSynchronizer(
                observer,
                poll_interval=0.05,
                timeout=15.0,
            ).wait_for_change(
                before,
                phases={"BLIND_SELECT"},
                require_complete=False,
            )
    except (OSError, RuntimeError, TimeoutError, ValueError, LiveShopNextRoundMouseError) as error:
        print("Live SHOP Next Round mouse validation -> FAIL")
        print(f"Reason -> {error}")
        return 2

    print(f"Phase after -> {after.phase}")
    print(f"State complete after -> {after.state_complete}")
    print(f"Money after -> {after.payload.get('money')}")
    print("SHOP -> BLIND_SELECT checkpoint verified -> True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
