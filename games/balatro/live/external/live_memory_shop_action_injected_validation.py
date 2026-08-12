from __future__ import annotations

import argparse
import hashlib
import json

from games.balatro.actions import (
    BUY_BOOSTER,
    BUY_CONSUMABLE,
    BUY_JOKER,
    BUY_VOUCHER,
    REFRESH_SHOP,
    BalatroAction,
)
from games.balatro.live.injected import (
    FirstPartyBalatroBridge,
    InjectedBridgeError,
    LiveMemoryInjectedActionDispatcher,
)
from games.balatro.live.protocol import LiveBalatroSnapshot

from .live_memory_observer import LiveMemoryBalatroObserver


_ACTIONS = (
    REFRESH_SHOP,
    BUY_JOKER,
    BUY_CONSUMABLE,
    BUY_VOUCHER,
    BUY_BOOSTER,
)

_AREA_BY_ACTION = {
    BUY_JOKER: "shop_jokers",
    BUY_CONSUMABLE: "shop_jokers",
    BUY_VOUCHER: "shop_vouchers",
    BUY_BOOSTER: "shop_boosters",
}

_CONSUMABLE_SETS = {"TAROT", "PLANET", "SPECTRAL"}


def _fingerprint(snapshot: LiveBalatroSnapshot) -> str:
    payload = {
        "phase": snapshot.phase,
        "state_complete": snapshot.state_complete,
        "payload": snapshot.payload,
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _money(snapshot: LiveBalatroSnapshot) -> float | None:
    value = snapshot.payload.get("money")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _cards(snapshot: LiveBalatroSnapshot, area_name: str) -> list[dict]:
    area = snapshot.payload.get(area_name)
    if not isinstance(area, dict):
        return []
    values = area.get("cards")
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, dict)]


def _item(
    snapshot: LiveBalatroSnapshot,
    action_name: str,
    index: int,
) -> dict | None:
    area_name = _AREA_BY_ACTION.get(action_name)
    if area_name is None:
        return None
    values = _cards(snapshot, area_name)
    if index < 0 or index >= len(values):
        return None
    return values[index]


def _label(item: dict) -> str:
    value = item.get("label") or item.get("ability_name") or item.get("center")
    return str(value) if value is not None else "<unknown>"


def _cost(item: dict) -> float | None:
    value = item.get("cost")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _ability_set(item: dict) -> str:
    value = item.get("ability_set") or item.get("set") or ""
    return str(value).upper()


def _guard_errors(
    snapshot: LiveBalatroSnapshot,
    *,
    action_name: str,
    expected_money: float,
    index: int | None = None,
    expected_label: str | None = None,
    expected_cost: float | None = None,
) -> list[str]:
    errors: list[str] = []

    if snapshot.phase != "SHOP":
        errors.append(f"expected SHOP, observed {snapshot.phase}")
    if not snapshot.state_complete:
        errors.append("SHOP state is not complete")

    money = _money(snapshot)
    if money is None:
        errors.append("observed shop money is unavailable")
    elif money != float(expected_money):
        errors.append(
            f"expected money {expected_money:g}, observed {money:g}"
        )

    if action_name == REFRESH_SHOP:
        return errors

    if action_name not in _AREA_BY_ACTION:
        errors.append(f"unsupported shop action {action_name}")
        return errors

    if index is None:
        errors.append("purchase action has no target index")
        return errors
    if index < 0:
        errors.append("purchase target index cannot be negative")
        return errors

    item = _item(snapshot, action_name, index)
    if item is None:
        area_name = _AREA_BY_ACTION[action_name]
        errors.append(
            f"{area_name} index {index} is not currently available"
        )
        return errors

    observed_label = _label(item)
    if expected_label is None:
        errors.append("purchase action has no expected label")
    elif observed_label != expected_label:
        errors.append(
            f"expected label {expected_label!r}, observed {observed_label!r}"
        )

    observed_cost = _cost(item)
    if expected_cost is None:
        errors.append("purchase action has no expected cost")
    elif observed_cost is None:
        errors.append("observed item cost is unavailable")
    elif observed_cost != float(expected_cost):
        errors.append(
            f"expected cost {expected_cost:g}, observed {observed_cost:g}"
        )

    ability_set = _ability_set(item)
    if action_name == BUY_JOKER and ability_set != "JOKER":
        errors.append(
            f"BUY_JOKER target is {ability_set or '<unknown>'}, not JOKER"
        )
    if action_name == BUY_CONSUMABLE and ability_set not in _CONSUMABLE_SETS:
        errors.append(
            "BUY_CONSUMABLE target is "
            f"{ability_set or '<unknown>'}, not Tarot/Planet/Spectral"
        )

    return errors


def _print_area(
    snapshot: LiveBalatroSnapshot,
    area_name: str,
    heading: str,
) -> None:
    values = _cards(snapshot, area_name)
    print(f"{heading} -> {len(values)}")
    for index, item in enumerate(values):
        cost = _cost(item)
        cost_text = "?" if cost is None else f"{cost:g}"
        set_name = _ability_set(item) or "UNKNOWN"
        center = item.get("center") or "?"
        print(
            f"  {index}: {_label(item)} | set={set_name} | "
            f"cost={cost_text} | center={center}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Guarded first-party injected validation for Balatro SHOP actions. "
            "Preview mode is read-only. --execute invokes exactly one shop "
            "action through the repo-owned Lua bridge and sends no mouse input."
        )
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--action", choices=_ACTIONS)
    parser.add_argument("--expect-money", type=float)
    parser.add_argument("--index", type=int)
    parser.add_argument("--expect-label")
    parser.add_argument("--expect-cost", type=float)
    args = parser.parse_args()

    purchase_fields = (args.index, args.expect_label, args.expect_cost)
    if args.execute:
        if args.action is None or args.expect_money is None:
            parser.error("--execute requires --action and --expect-money")
        if args.action == REFRESH_SHOP:
            if any(value is not None for value in purchase_fields):
                parser.error(
                    "REFRESH_SHOP does not accept --index, --expect-label, "
                    "or --expect-cost"
                )
        elif any(value is None for value in purchase_fields):
            parser.error(
                "purchase execution requires --index, --expect-label, "
                "and --expect-cost"
            )
    else:
        if any(
            value is not None
            for value in (
                args.action,
                args.expect_money,
                args.index,
                args.expect_label,
                args.expect_cost,
            )
        ):
            parser.error(
                "execution expectations are only valid with --execute"
            )

    with LiveMemoryBalatroObserver() as observer:
        snapshot = observer.observe()
        if snapshot.phase != "SHOP":
            parser.error(
                f"shop injected validation requires SHOP, observed {snapshot.phase}"
            )
        if not snapshot.state_complete:
            parser.error("SHOP is not complete; wait for the UI to settle")

        print("Live-memory first-party injected shop validation -> READY")
        print("Observation source -> live Balatro process memory")
        print("Execution backend -> game-ai-framework injected Lua bridge")
        print("Runtime loader -> none (fused LÖVE archive)")
        print("Lovely required -> False")
        print("Steamodded required -> False")
        print("BalatroBot required -> False")
        print("Mouse calibration required -> False")
        print(f"Phase -> {snapshot.phase}")
        money = _money(snapshot)
        print(f"Money -> {'?' if money is None else f'{money:g}'}")
        _print_area(snapshot, "shop_jokers", "Shop cards")
        _print_area(snapshot, "shop_vouchers", "Vouchers")
        _print_area(snapshot, "shop_boosters", "Boosters")
        print(
            "Supported injected shop actions -> "
            + ", ".join(_ACTIONS)
        )
        print("Observation process writes -> False")

        if not args.execute:
            print("Execution guard -> PREVIEW ONLY")
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        assert args.action is not None
        assert args.expect_money is not None
        guard_errors = _guard_errors(
            snapshot,
            action_name=args.action,
            expected_money=args.expect_money,
            index=args.index,
            expected_label=args.expect_label,
            expected_cost=args.expect_cost,
        )
        if guard_errors:
            print("Execution guard -> BLOCKED")
            for error in guard_errors:
                print(f"Reason -> {error}")
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        latest = observer.observe()
        if (
            latest.sequence != snapshot.sequence
            or _fingerprint(latest) != _fingerprint(snapshot)
        ):
            print("Execution guard -> BLOCKED")
            print(
                "Reason -> live SHOP state changed before dispatch; "
                "re-run from the new checkpoint"
            )
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        bridge = FirstPartyBalatroBridge()
        try:
            bridge.ping()
        except InjectedBridgeError as error:
            print("Execution guard -> BLOCKED")
            print(f"Reason -> injected bridge unavailable: {error}")
            print("Injected bridge command sent -> False")
            print("Mouse input sent -> False")
            return 0

        action = (
            BalatroAction(REFRESH_SHOP)
            if args.action == REFRESH_SHOP
            else BalatroAction(
                args.action,
                target={"area_index": int(args.index)},
            )
        )

        print("Execution guard -> PASS")
        print(
            "WARNING -> --execute is armed: one real in-process Balatro "
            "shop action will now be invoked"
        )
        print(f"Execution scope -> exactly one {args.action} action")
        if args.action != REFRESH_SHOP:
            target = _item(latest, args.action, int(args.index))
            assert target is not None
            print(
                f"Armed target -> index={args.index} "
                f"label={_label(target)!r} cost={_cost(target):g}"
            )
        print("Mouse input sent -> False")

        try:
            result = LiveMemoryInjectedActionDispatcher(
                observer,
                bridge=bridge,
            ).dispatch(
                action,
                snapshot=latest,
            )
        except (InjectedBridgeError, RuntimeError) as error:
            print("Injected execution -> FAILED")
            print(f"Reason -> {error}")
            print("Follow-up action executed -> False")
            return 1

        print("Injected bridge command sent -> True")
        print(f"Checkpoint sequence -> {result.after.sequence}")
        print(f"Phase after -> {result.after.phase}")
        after_money = _money(result.after)
        print(
            f"Money after -> "
            f"{'?' if after_money is None else f'{after_money:g}'}"
        )
        print("Follow-up action executed -> False")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
