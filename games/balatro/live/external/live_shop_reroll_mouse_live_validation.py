from __future__ import annotations

import argparse
import time

from .live_memory_observer import LiveMemoryBalatroObserver
from .live_shop_reroll_mouse import (
    LiveMemoryShopRerollMouseExecutor,
    LiveShopRerollMouseError,
)
from .mouse import BalatroMouseController


def _main_offer_signature(snapshot) -> tuple[tuple[object, object, object, object], ...]:
    cards = (snapshot.payload.get("shop_jokers") or {}).get("cards") or []
    return tuple(
        (
            card.get("live_id"),
            card.get("center"),
            card.get("label") or card.get("ability_name"),
            card.get("cost"),
        )
        for card in cards
    )


def _reroll_postcondition(before, after) -> tuple[bool, str]:
    if after.sequence <= before.sequence:
        return False, "live snapshot has not changed"
    if after.phase != "SHOP":
        return False, f"phase changed to {after.phase}, expected SHOP"

    before_offers = _main_offer_signature(before)
    after_offers = _main_offer_signature(after)
    if after_offers == before_offers:
        return False, "visible main-shop offers have not changed"

    before_money = before.payload.get("money")
    after_money = after.payload.get("money")
    if isinstance(before_money, (int, float)) and isinstance(after_money, (int, float)):
        if float(after_money) > float(before_money):
            return False, f"money increased from {before_money} to {after_money}"

    return True, "reroll applied"


def _wait_for_reroll(observer, before, timeout: float = 15.0):
    deadline = time.monotonic() + timeout
    last_reason = "no changed snapshot observed"
    while time.monotonic() < deadline:
        after = observer.observe()
        ok, reason = _reroll_postcondition(before, after)
        if ok:
            return after
        last_reason = reason
        time.sleep(0.05)
    raise TimeoutError("timed out verifying live SHOP reroll: " + last_reason)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or execute exactly one Balatro SHOP Reroll using normal mouse "
            "input. The click is allowed only after live cursor-hover identity confirms "
            "reroll_shop/can_reroll, then live memory verifies the offers changed."
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="arm normal mouse input and perform exactly one verified Reroll click",
    )
    args = parser.parse_args()

    try:
        with LiveMemoryBalatroObserver() as observer:
            mouse = BalatroMouseController(armed=args.execute, hover_delay=0.0)
            executor = LiveMemoryShopRerollMouseExecutor(
                observer=observer,
                mouse=mouse,
            )
            snapshot, window = executor.preview()
            print("Live SHOP Reroll mouse validation -> READY")
            print("Observation source -> live Balatro process memory")
            print(f"Phase before -> {snapshot.phase}")
            print("Process writes/injection -> False")
            print("Hidden RNG/deck traversal -> False")
            print(f"Money before -> {snapshot.payload.get('money')}")
            print(
                "Balatro client rect -> "
                f"left={window.client_rect.left} top={window.client_rect.top} "
                f"width={window.client_rect.width} height={window.client_rect.height}"
            )
            print(f"Main offers before -> {_main_offer_signature(snapshot)!r}")

            if not args.execute:
                print("Mouse movement sent -> False")
                print("Mouse clicks sent -> False")
                print(
                    "Re-run with --execute to locate a live-hit-tested Reroll point "
                    "and send exactly one normal mouse click there."
                )
                return 0

            before, target = executor.dispatch()
            print("Mouse movement sent -> True")
            print("Mouse clicks sent -> True")
            print(f"Reroll node address -> 0x{target.node_address:x}")
            print(f"Reroll button -> {target.button!r}")
            print(f"Reroll func -> {target.func!r}")
            print(f"Reroll id -> {target.control_id!r}")
            print(
                "Verified live Reroll point -> "
                f"x={target.screen_point.x} y={target.screen_point.y}"
            )
            print(f"Verified Reroll hit signal -> {target.hit_signal}")
            print(f"Reroll probes required -> {target.probes}")
            print("Waiting for live reroll postcondition -> SHOP")

            after = _wait_for_reroll(observer, before)
    except (OSError, RuntimeError, TimeoutError, ValueError, LiveShopRerollMouseError) as error:
        print("Live SHOP Reroll mouse validation -> FAIL")
        print(f"Reason -> {error}")
        return 2

    print(f"Phase after -> {after.phase}")
    print(f"State complete after -> {after.state_complete}")
    print(f"Money after -> {after.payload.get('money')}")
    print(f"Main offers after -> {_main_offer_signature(after)!r}")
    print("Main-shop offers changed -> True")
    print("Money did not increase -> True")
    print("Live SHOP Reroll checkpoint verified -> True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
