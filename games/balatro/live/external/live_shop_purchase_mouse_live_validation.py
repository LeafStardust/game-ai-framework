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


def _fmt_geometry(value: dict[str, float]) -> str:
    return " ".join(
        f"{name}={value[name]:.6f}"
        for name in ("x", "y", "w", "h", "r", "scale")
        if name in value
    )


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


def _owned_destination(snapshot, target: LiveShopItemTarget) -> tuple[str, bool]:
    ability_set = (target.ability_set or "").casefold()
    if ability_set == "joker":
        cards = _cards(snapshot, "jokers")
        return "jokers", _contains_target(cards, target)
    if ability_set in {"tarot", "planet", "spectral", "consumeable", "consumable"}:
        cards = _cards(snapshot, "consumables")
        return "consumables", _contains_target(cards, target)

    joker_match = _contains_target(_cards(snapshot, "jokers"), target)
    consumable_match = _contains_target(_cards(snapshot, "consumables"), target)
    return "jokers/consumables", joker_match or consumable_match


def _purchase_postcondition(before, after, target: LiveShopItemTarget) -> tuple[bool, str]:
    if after.sequence <= before.sequence:
        return False, "live snapshot has not changed"
    if after.phase != "SHOP":
        return False, f"phase changed to {after.phase}, expected SHOP"

    before_money = before.payload.get("money")
    after_money = after.payload.get("money")
    if not isinstance(before_money, (int, float)) or not isinstance(after_money, (int, float)):
        return False, "money is unavailable"
    expected_money = float(before_money) - target.cost
    if float(after_money) != expected_money:
        return False, f"money={after_money}, expected={expected_money:g}"

    if _contains_target(_cards(after, "shop_jokers"), target):
        return False, "target is still present in main-shop offers"

    destination, owned = _owned_destination(after, target)
    if not owned:
        return False, f"target is not yet present in owned {destination}"

    return True, destination


def _wait_for_purchase(observer, before, target: LiveShopItemTarget, timeout: float = 15.0):
    deadline = time.monotonic() + timeout
    last_reason = "no changed snapshot observed"
    while time.monotonic() < deadline:
        after = observer.observe()
        ok, reason = _purchase_postcondition(before, after, target)
        if ok:
            return after, reason
        last_reason = reason
        time.sleep(0.05)
    raise TimeoutError("timed out verifying live shop purchase: " + last_reason)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or execute one ordinary Buy action for a live main-shop item. "
            "The executor uses the card-relative Buy template first, requires Balatro's "
            "live hover identity before clicking, then verifies money/offer/ownership."
        )
    )
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="arm normal mouse input and perform exactly one verified Buy click",
    )
    args = parser.parse_args()
    if args.index < 0:
        parser.error("--index cannot be negative")

    try:
        with LiveMemoryBalatroObserver() as observer:
            mouse = BalatroMouseController(armed=args.execute, hover_delay=0.0)
            executor = LiveMemoryShopPurchaseMouseExecutor(
                observer=observer,
                mouse=mouse,
                action="buy",
            )

            snapshot, item, window = executor.preview(args.index)
            print("Live SHOP purchase mouse validation -> READY")
            print("Observation source -> live Balatro process memory")
            print(f"Phase before -> {snapshot.phase}")
            print("Process writes/injection -> False")
            print("Hidden RNG/deck traversal -> False")
            print(f"Target area -> {item.area}")
            print(f"Target index -> {item.index}")
            print(f"Target label -> {item.label!r}")
            print(f"Target live_id -> {item.live_id!r}")
            print(f"Target ability_set -> {item.ability_set!r}")
            print(f"Target cost -> {item.cost:g}")
            print(f"Money before -> {snapshot.payload.get('money')}")
            print(f"Target geometry -> {_fmt_geometry(item.geometry)}")
            print(
                "Balatro client rect -> "
                f"left={window.client_rect.left} top={window.client_rect.top} "
                f"width={window.client_rect.width} height={window.client_rect.height}"
            )
            print(
                "Live item hover center -> "
                f"x={item.screen_center.x} y={item.screen_center.y}"
            )

            if not args.execute:
                print("Mouse movement sent -> False")
                print("Mouse clicks sent -> False")
                print(
                    "Re-run with --execute to template-locate and live-verify the "
                    "ordinary Buy control, then send exactly one normal mouse click."
                )
                return 0

            before, clicked_item, verified = executor.dispatch(args.index)
            buy = verified.control
            print("Mouse movement sent -> True")
            print("Mouse clicks sent -> True")
            print(
                "Hovered live item center -> "
                f"x={clicked_item.screen_center.x} y={clicked_item.screen_center.y}"
            )
            print("Buy control button -> " + repr(buy.button))
            print("Buy control func -> " + repr(buy.func))
            print("Buy control id -> " + repr(buy.control_id))
            print(f"Buy nested geometry source -> {buy.geometry_source}")
            print(f"Buy nested geometry -> {_fmt_geometry(buy.geometry)}")
            print(
                "Nested-geometry guessed Buy center -> "
                f"x={buy.screen_center.x} y={buy.screen_center.y}"
            )
            print(
                "Verified live Buy point -> "
                f"x={verified.screen_point.x} y={verified.screen_point.y}"
            )
            print(f"Verified Buy hit signal -> {verified.hit_signal}")
            print(f"Buy location source -> {verified.location_source}")
            print(f"Buy probes required -> {verified.probes}")
            print(f"Local live search used -> {verified.used_local_search}")
            print(f"Fallback search used -> {verified.used_fallback_search}")
            print("Waiting for live purchase postcondition -> SHOP")

            after, destination = _wait_for_purchase(observer, before, clicked_item)
    except (OSError, RuntimeError, TimeoutError, ValueError, LiveShopPurchaseMouseError) as error:
        print("Live SHOP purchase mouse validation -> FAIL")
        print(f"Reason -> {error}")
        return 2

    print(f"Phase after -> {after.phase}")
    print(f"State complete after -> {after.state_complete}")
    print(f"Money after -> {after.payload.get('money')}")
    print(f"Owned destination -> {destination}")
    print("Target removed from main-shop offers -> True")
    print("Target present in owned items -> True")
    print("Live SHOP purchase checkpoint verified -> True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
