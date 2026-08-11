from __future__ import annotations

import argparse
import time
from typing import Any

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _array_table_values,
    _number,
    _primitive,
    _table_fields,
)
from .live_ui_transform import BalatroLogicalViewport
from .mouse import BalatroMouseController
from .window import BalatroWindowLocator


def _flatten_state(decoder, address: int) -> dict[str, Any]:
    card = decoder.string_fields(address)
    result: dict[str, Any] = {}

    # Direct primitive fields that may expose hover/collision state on different
    # Balatro/LuaJIT builds.
    for name, value in card.items():
        if any(token in name.casefold() for token in ("hover", "focus", "click")):
            primitive = _primitive(value)
            if primitive is not None:
                result[name] = primitive

    states = _table_fields(decoder, card.get("states"))
    for state_name, state_value in states.items():
        primitive = _primitive(state_value)
        if primitive is not None:
            result[f"states.{state_name}"] = primitive
            continue
        nested = _table_fields(decoder, state_value)
        for field_name, field_value in nested.items():
            primitive = _primitive(field_value)
            if primitive is not None:
                result[f"states.{state_name}.{field_name}"] = primitive

    hover_offset = _table_fields(decoder, card.get("hover_offset"))
    for field_name, field_value in hover_offset.items():
        primitive = _primitive(field_value)
        if primitive is not None:
            result[f"hover_offset.{field_name}"] = primitive

    return result


def _differences(before: dict[str, Any], after: dict[str, Any]) -> dict[str, tuple[Any, Any]]:
    keys = sorted(set(before) | set(after))
    return {
        key: (before.get(key), after.get(key))
        for key in keys
        if before.get(key) != after.get(key)
    }


def _active_hover_truths(state: dict[str, Any]) -> tuple[str, ...]:
    """Return fields that mean a card is actively hovered, not merely hoverable.

    Balatro exposes ``states.hover.can`` on every hover-capable card, while
    ``states.hover.is`` becomes true only for the card currently under the cursor.
    Direct boolean hover fields are accepted as a compatibility fallback.
    """

    active: list[str] = []
    for key, value in state.items():
        if value is not True:
            continue
        folded = key.casefold()
        if folded == "hover" or folded.endswith(".hover"):
            active.append(key)
            continue
        if "hover" in folded and folded.endswith(".is"):
            active.append(key)
    return tuple(active)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Move the normal Windows cursor to one live-memory-derived Balatro hand "
            "card center and verify the hovered card from Balatro's live state. "
            "No mouse click is sent."
        )
    )
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--settle", type=float, default=0.30)
    args = parser.parse_args()
    if args.index < 0:
        parser.error("--index cannot be negative")
    if args.settle < 0:
        parser.error("--settle cannot be negative")

    try:
        locator = BalatroWindowLocator()
        window = locator.find()
        with LiveMemoryBalatroObserver() as observer:
            decoder, _, root = observer._root()
            snapshot = observer.observe()

            hand_area = _table_fields(decoder, root.get("hand"))
            raw_cards = _array_table_values(decoder, hand_area.get("cards"))
            public_cards = (snapshot.payload.get("hand") or {}).get("cards") or []
            if not raw_cards or len(raw_cards) != len(public_cards):
                raise RuntimeError(
                    "live hand card addresses do not match normalized live hand count"
                )
            if args.index >= len(raw_cards):
                raise RuntimeError(
                    f"--index {args.index} is outside current hand size {len(raw_cards)}"
                )

            tile_w = _number(root.get("TILE_W"))
            tile_h = _number(root.get("TILE_H"))
            if tile_w is None or tile_h is None:
                raise RuntimeError("Balatro logical TILE_W/TILE_H are unavailable")

            target = public_cards[args.index]
            geometry = target.get("ui") or {}
            transform = BalatroLogicalViewport(
                float(tile_w),
                float(tile_h),
                window.client_rect,
            )
            point = transform.card_center(geometry)

            before = {
                index: _flatten_state(decoder, address)
                for index, (_, address) in enumerate(raw_cards)
            }

            mouse = BalatroMouseController(armed=True, hover_delay=0.0)
            mouse.focus(window)
            # Refresh after focus in case Windows changed the client placement.
            window = locator.refresh(window.handle)
            transform = BalatroLogicalViewport(
                float(tile_w),
                float(tile_h),
                window.client_rect,
            )
            point = transform.card_center(geometry)
            mouse.move_screen(point)
            if args.settle:
                time.sleep(args.settle)

            after = {
                index: _flatten_state(decoder, address)
                for index, (_, address) in enumerate(raw_cards)
            }
    except Exception as error:
        print("Live UI hover validation -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse clicks sent -> False")
        return 2

    target_value = target.get("value") or {}
    print("Live UI hover validation -> DIAGNOSTIC")
    print("Observation source -> live Balatro process memory")
    print("Mouse movement sent -> True")
    print("Mouse clicks sent -> False")
    print("Process writes/injection -> False")
    print(
        f"Target -> H{args.index}: {target_value.get('rank')} / "
        f"{target_value.get('suit')} live_id={target.get('live_id')}"
    )
    print(f"Computed screen center -> ({point.x},{point.y})")

    changed_cards: list[int] = []
    for index in range(len(raw_cards)):
        changes = _differences(before[index], after[index])
        truths = _active_hover_truths(after[index])
        if changes or truths:
            changed_cards.append(index)
            print(f"  H{index} live state:")
            for key, (old, new) in changes.items():
                print(f"    {key}: {old!r} -> {new!r}")
            for key in truths:
                if key not in changes:
                    print(f"    {key}: True")

    target_hover = _active_hover_truths(after[args.index])
    other_hover = {
        index: _active_hover_truths(after[index])
        for index in range(len(raw_cards))
        if index != args.index and _active_hover_truths(after[index])
    }

    if target_hover and not other_hover:
        print("Hovered-card identity -> PASS")
        print("Target hover field(s) -> " + ", ".join(target_hover))
        print("Coordinate transform hover validation -> PASS")
        return 0

    print("Hovered-card identity -> INCONCLUSIVE")
    print(
        "Cards with observable hover/state activity -> "
        + (",".join(map(str, changed_cards)) if changed_cards else "none")
    )
    print("Coordinate transform hover validation -> NOT_YET_VALIDATED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
