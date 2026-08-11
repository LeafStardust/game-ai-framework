from __future__ import annotations

import argparse
import time

from .live_memory_observer import LiveMemoryBalatroObserver
from .live_shop_purchase_mouse import (
    LiveMemoryShopPurchaseMouseExecutor,
    LiveShopItemTarget,
    LiveShopPurchaseMouseError,
)
from .mouse import BalatroMouseController


def _cards(snapshot, name: str) -> list[dict]:
    return list((snapshot.payload.get(name) or {}).get("cards") or [])


def _contains_target(cards: list[dict], target: LiveShopItemTarget) -> bool:
    if target.live_id is not None:
        return any(card.get("live_id") == target.live_id for card in cards)
    return any(
        (card.get("label") or card.get("ability_name") or card.get("center"))
        == target.label
        for card in cards
    )


def _postcondition(before, after, target: LiveShopItemTarget) -> tuple[bool, str]:
    if after.sequence <= before.sequence:
        return False, "live snapshot has not changed"

    before_money = before.payload.get("money")
    after_money = after.payload.get("money")
    if not isinstance(before_money, (int, float)) or not isinstance(after_money, (int, float)):
        return False, "money is unavailable"
    expected_money = float(before_money) - target.cost
    if float(after_money) != expected_money:
        return False, f"money={after_money}, expected={expected_money:g}"

    if _contains_target(_cards(after, "shop_jokers"), target):
        return False, "target is still present in main-shop offers"

    return True, "money deducted exactly and offer consumed"


def _wait_for_result(observer, before, target: LiveShopItemTarget, timeout: float = 15.0):
    deadline = time.monotonic() + timeout
    last_reason = "no changed snapshot observed"
    while time.monotonic() < deadline:
        after = observer.observe()
        ok, reason = _postcondition(before, after, target)
        if ok:
            return after, reason
        last_reason = reason
        time.sleep(0.05)
    raise TimeoutError("timed out verifying Buy & Use: " + last_reason)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or execute one main-shop Buy & Use action. The executor clicks "
            "the item first, requires the generated Buy & Use child, then targets the "
            "card-relative template and verifies exact buy_from_shop/can_buy_and_use."
        )
    )
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.index < 0:
        parser.error("--index cannot be negative")

    try:
        with LiveMemoryBalatroObserver() as observer:
            mouse = BalatroMouseController(armed=args.execute, hover_delay=0.0)
            executor = LiveMemoryShopPurchaseMouseExecutor(
                observer=observer,
                mouse=mouse,
                action="buy_and_use",
            )
            snapshot, item, window = executor.preview(args.index)

            print("Live SHOP Buy & Use mouse validation -> READY")
            print("Observation source -> live Balatro process memory")
            print(f"Phase before -> {snapshot.phase}")
            print("Process writes/injection -> False")
            print("Hidden RNG/deck traversal -> False")
            print(f"Target index -> {item.index}")
            print(f"Target label -> {item.label!r}")
            print(f"Target live_id -> {item.live_id!r}")
            print(f"Target ability_set -> {item.ability_set!r}")
            print(f"Target cost -> {item.cost:g}")
            print(f"Money before -> {snapshot.payload.get('money')}")
            print(
                "Live item center -> "
                f"x={item.screen_center.x} y={item.screen_center.y}"
            )
            print(
                "Balatro client rect -> "
                f"left={window.client_rect.left} top={window.client_rect.top} "
                f"width={window.client_rect.width} height={window.client_rect.height}"
            )

            if not args.execute:
                print("Mouse movement sent -> False")
                print("Mouse clicks sent -> False")
                print(
                    "Re-run with --execute to click the item once, verify Buy & Use "
                    "appears, and click that generated control once."
                )
                return 0

            before, clicked_item, verified = executor.dispatch(args.index)
            control = verified.control
            print("Mouse movement sent -> True")
            print("Mouse clicks sent -> True")
            print("Clicks sent -> 2")
            print(
                "Item selection click -> "
                f"x={verified.item_click_point.x} y={verified.item_click_point.y}"
            )
            print("Item selection exposed expected Buy & Use control -> True")
            print(f"Control button -> {control.button!r}")
            print(f"Control func -> {control.func!r}")
            print(f"Control id -> {control.control_id!r}")
            print(
                "Verified live Buy & Use point -> "
                f"x={verified.screen_point.x} y={verified.screen_point.y}"
            )
            print(f"Verified hit signal -> {verified.hit_signal}")
            print(f"Location source -> {verified.location_source}")
            print(f"Hover probes required -> {verified.probes}")
            print(f"Local live search used -> {verified.used_local_search}")
            print(f"Fallback search used -> {verified.used_fallback_search}")
            print("Waiting for live Buy & Use postcondition")

            after, reason = _wait_for_result(observer, before, clicked_item)
    except (OSError, RuntimeError, TimeoutError, ValueError, LiveShopPurchaseMouseError) as error:
        print("Live SHOP Buy & Use mouse validation -> FAIL")
        print(f"Reason -> {error}")
        return 2

    print(f"Phase after -> {after.phase}")
    print(f"State complete after -> {after.state_complete}")
    print(f"Money after -> {after.payload.get('money')}")
    print("Target removed from main-shop offers -> True")
    print(f"Postcondition -> {reason}")
    print("Live SHOP Buy & Use checkpoint verified -> True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
