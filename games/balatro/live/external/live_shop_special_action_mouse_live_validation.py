from __future__ import annotations

import argparse
import time

from .live_memory_observer import LiveMemoryBalatroObserver
from .live_shop_special_action_mouse import (
    AREA_PAYLOADS,
    LiveMemoryShopSpecialActionMouseExecutor,
    LiveShopSpecialActionMouseError,
    LiveShopSpecialItemTarget,
)
from .mouse import BalatroMouseController


def _cards(snapshot, area: str) -> list[dict]:
    return list((snapshot.payload.get(AREA_PAYLOADS[area]) or {}).get("cards") or [])


def _contains_target(cards: list[dict], target: LiveShopSpecialItemTarget) -> bool:
    if target.live_id is not None:
        return any(card.get("live_id") == target.live_id for card in cards)
    return any(
        (card.get("label") or card.get("ability_name") or card.get("center")) == target.label
        for card in cards
    )


def _postcondition(before, after, target: LiveShopSpecialItemTarget) -> tuple[bool, str]:
    if after.sequence <= before.sequence:
        return False, "live snapshot has not changed"

    before_money = before.payload.get("money")
    after_money = after.payload.get("money")
    if not isinstance(before_money, (int, float)) or not isinstance(after_money, (int, float)):
        return False, "money is unavailable"
    expected_money = float(before_money) - target.cost
    if float(after_money) != expected_money:
        return False, f"money={after_money}, expected={expected_money:g}"

    if target.area == "vouchers":
        if after.phase != "SHOP":
            return False, f"voucher redemption changed phase to {after.phase}, expected SHOP"
        if _contains_target(_cards(after, "vouchers"), target):
            return False, "redeemed voucher is still present in shop_vouchers"
        return True, "voucher redeemed"

    if target.area == "boosters":
        if after.phase == "SHOP":
            return False, "booster has not entered its pack-opening phase yet"
        return True, f"booster opened into {after.phase}"

    return False, f"unsupported area {target.area}"


def _wait_for_postcondition(observer, before, target, timeout: float = 15.0):
    deadline = time.monotonic() + timeout
    last_reason = "no changed snapshot observed"
    while time.monotonic() < deadline:
        after = observer.observe()
        ok, reason = _postcondition(before, after, target)
        if ok:
            return after, reason
        last_reason = reason
        time.sleep(0.05)
    raise TimeoutError("timed out verifying special SHOP action: " + last_reason)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or execute one live Voucher Redeem or Booster Open action. "
            "Execution clicks the special SHOP card once, verifies the generated "
            "Redeem/Open control from live memory, then clicks that control once."
        )
    )
    parser.add_argument("--area", choices=sorted(AREA_PAYLOADS), required=True)
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.index < 0:
        parser.error("--index cannot be negative")

    try:
        with LiveMemoryBalatroObserver() as observer:
            mouse = BalatroMouseController(armed=args.execute, hover_delay=0.0)
            executor = LiveMemoryShopSpecialActionMouseExecutor(
                observer=observer,
                mouse=mouse,
            )
            snapshot, item, window = executor.preview(args.area, args.index)

            print("Live SHOP special action mouse validation -> READY")
            print("Observation source -> live Balatro process memory")
            print(f"Phase before -> {snapshot.phase}")
            print("Process writes/injection -> False")
            print("Hidden RNG/deck traversal -> False")
            print(f"Area -> {item.area}")
            print(f"Target index -> {item.index}")
            print(f"Target label -> {item.label!r}")
            print(f"Target live_id -> {item.live_id!r}")
            print(f"Target cost -> {item.cost:g}")
            print(f"Money before -> {snapshot.payload.get('money')}")
            print(
                "Balatro client rect -> "
                f"left={window.client_rect.left} top={window.client_rect.top} "
                f"width={window.client_rect.width} height={window.client_rect.height}"
            )
            print(f"Live item center -> x={item.screen_center.x} y={item.screen_center.y}")

            if not args.execute:
                print("Mouse movement sent -> False")
                print("Mouse clicks sent -> False")
                print(
                    "Re-run with --execute to click the item once, verify its generated "
                    "action control, and click that control once."
                )
                return 0

            before, clicked_item, target = executor.dispatch(args.area, args.index)
            print("Mouse movement sent -> True")
            print("Mouse clicks sent -> True")
            print("Clicks sent -> 2")
            if target.item_click_point is not None:
                print(
                    "Item selection click -> "
                    f"x={target.item_click_point.x} y={target.item_click_point.y}"
                )
            print("Item selection exposed expected action control -> True")
            print(f"Action node address -> 0x{target.node_address:x}")
            print(f"Action button -> {target.button!r}")
            print(f"Action func -> {target.func!r}")
            print(f"Action id -> {target.control_id!r}")
            print(
                "Verified live action point -> "
                f"x={target.screen_point.x} y={target.screen_point.y}"
            )
            print(f"Verified action hit signal -> {target.hit_signal}")
            print(f"Action location source -> {target.location_source}")
            print(f"Local live search used -> {target.used_local_search}")
            print(f"Fallback search used -> {target.used_fallback_search}")
            print(f"Action probes required -> {target.probes}")
            print("Waiting for live special-action postcondition")

            after, result = _wait_for_postcondition(observer, before, clicked_item)
    except (OSError, RuntimeError, TimeoutError, ValueError, LiveShopSpecialActionMouseError) as error:
        print("Live SHOP special action mouse validation -> FAIL")
        print(f"Reason -> {error}")
        return 2

    print(f"Phase after -> {after.phase}")
    print(f"State complete after -> {after.state_complete}")
    print(f"Money after -> {after.payload.get('money')}")
    print(f"Postcondition -> {result}")
    if clicked_item.area == "vouchers":
        print("Voucher removed from shop_vouchers -> True")
        print("Live SHOP Voucher Redeem checkpoint verified -> True")
    else:
        print("Booster left SHOP for pack-opening phase -> True")
        print("Live SHOP Booster Open checkpoint verified -> True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
