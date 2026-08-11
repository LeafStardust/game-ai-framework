from __future__ import annotations

import argparse
import time

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _array_table_values,
    _geometry,
    _number,
    _primitive,
    _table_fields,
)
from .live_ui_pack_controls_diagnostic import _scan as _scan_pack_controls
from .live_ui_transform import BalatroLogicalViewport
from .mouse import BalatroMouseController
from .window import BalatroWindowLocator


INTERESTING_MARKERS = ("highlight", "select", "chosen", "choice")


def _table_address(value) -> int | None:
    if value is None or value.kind != "table":
        return None
    return int(value.value)


def _pack_area(decoder, root: dict) -> tuple[int, dict]:
    value = root.get("pack_cards")
    address = _table_address(value)
    if address is None:
        raise RuntimeError("G.pack_cards is missing")
    return address, _table_fields(decoder, value)


def _pack_card_addresses(decoder, area: dict) -> list[int]:
    return [address for _, address in _array_table_values(decoder, area.get("cards"))]


def _card_label(decoder, address: int) -> tuple[str | None, object, object]:
    card = decoder.string_fields(address)
    base = _table_fields(decoder, card.get("base"))
    ability = _table_fields(decoder, card.get("ability"))
    config = _table_fields(decoder, card.get("config"))
    center = _table_fields(decoder, config.get("center"))
    label = (
        _primitive(card.get("label"))
        or _primitive(ability.get("name"))
        or _primitive(center.get("name"))
    )
    return label, _primitive(base.get("value")), _primitive(base.get("suit"))


def _state_flag(decoder, fields: dict, name: str, key: str) -> object:
    states = _table_fields(decoder, fields.get("states"))
    state = _table_fields(decoder, states.get(name))
    return _primitive(state.get(key))


def _selection_markers(decoder, fields: dict) -> list[str]:
    result: list[str] = []
    for name, value in sorted(fields.items()):
        primitive = _primitive(value)
        if primitive is None:
            continue
        if any(token in name.casefold() for token in INTERESTING_MARKERS):
            result.append(f"{name}={primitive!r}")
    config = _table_fields(decoder, fields.get("config"))
    for name, value in sorted(config.items()):
        primitive = _primitive(value)
        if primitive is None:
            continue
        if any(token in name.casefold() for token in INTERESTING_MARKERS):
            result.append(f"config.{name}={primitive!r}")
    return result


def _highlighted_addresses(decoder, area: dict) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {}
    for name, value in sorted(area.items()):
        if value.kind != "table" or not any(
            token in name.casefold() for token in INTERESTING_MARKERS
        ):
            continue
        addresses = [address for _, address in _array_table_values(decoder, value)]
        if addresses:
            result[name] = addresses
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preview or send exactly one normal mouse click to one live pack card, "
            "then report the resulting pack/highlight/control state without any "
            "second action."
        )
    )
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--settle", type=float, default=0.60)
    args = parser.parse_args()
    if args.index < 0:
        parser.error("--index cannot be negative")
    if args.settle < 0:
        parser.error("--settle cannot be negative")

    try:
        locator = BalatroWindowLocator()
        window = locator.find()
        with LiveMemoryBalatroObserver() as observer:
            before = observer.observe()
            if not before.phase.endswith("_PACK"):
                raise RuntimeError(f"Balatro is in {before.phase}, expected *_PACK")

            decoder, _, root = observer._root()
            tile_w = _number(root.get("TILE_W"))
            tile_h = _number(root.get("TILE_H"))
            if tile_w is None or tile_h is None or tile_w <= 0 or tile_h <= 0:
                raise RuntimeError("missing positive G.TILE_W / G.TILE_H")

            _, area = _pack_area(decoder, root)
            cards = _pack_card_addresses(decoder, area)
            if args.index >= len(cards):
                raise RuntimeError(
                    f"index {args.index} out of range for {len(cards)} pack cards"
                )
            card_address = cards[args.index]
            card = decoder.string_fields(card_address)
            geometry = _geometry(decoder, card.get("T"))
            if not all(name in geometry for name in ("x", "y", "w", "h")):
                raise RuntimeError("target pack card has no complete live geometry")
            label, rank, suit = _card_label(decoder, card_address)
            click_can = _state_flag(decoder, card, "click", "can")
            if click_can is not True:
                raise RuntimeError(
                    f"target pack card is not live-clickable: states.click.can={click_can!r}"
                )

            mouse = BalatroMouseController(armed=args.execute, hover_delay=0.0)
            mouse.focus(window)
            window = locator.refresh(window.handle)

            # Re-resolve the same pack card after focus acquisition.
            decoder, _, root = observer._root()
            _, area = _pack_area(decoder, root)
            cards = _pack_card_addresses(decoder, area)
            if args.index >= len(cards):
                raise RuntimeError("target pack card disappeared before probe")
            card_address = cards[args.index]
            card = decoder.string_fields(card_address)
            geometry = _geometry(decoder, card.get("T"))
            transform = BalatroLogicalViewport(float(tile_w), float(tile_h), window.client_rect)
            point = transform.card_center(geometry)
            mouse.move_screen(point)
            time.sleep(0.10)

            decoder, _, root = observer._root()
            controller = _table_fields(decoder, root.get("CONTROLLER"))
            cursor_hover = _table_fields(decoder, controller.get("cursor_hover"))
            hover_target = _table_address(cursor_hover.get("target"))
            if hover_target != card_address:
                raise RuntimeError(
                    "live cursor target does not match requested pack card before click: "
                    f"target={hover_target!r}, card=0x{card_address:x}"
                )

            print("Live pack card single-click probe -> READY")
            print("Observation source -> live Balatro process memory")
            print(f"Phase before -> {before.phase}")
            print("Process writes/injection -> False")
            print("Hidden RNG/deck traversal -> False")
            print(f"Target index -> {args.index}")
            print(f"Target address -> 0x{card_address:x}")
            print(f"Target label -> {label!r}")
            print(f"Target rank/suit -> {rank!r}/{suit!r}")
            print(f"Target states.click.can -> {click_can!r}")
            print(f"Verified live card point -> x={point.x} y={point.y}")
            print(f"Pack card count before -> {len(cards)}")
            print(f"Selection markers before -> {_selection_markers(decoder, card)!r}")
            print(f"Highlighted arrays before -> {_highlighted_addresses(decoder, area)!r}")

            if not args.execute:
                print("Mouse movement sent -> True")
                print("Mouse clicks sent -> False")
                print("Re-run with --execute to send exactly one click to this verified pack card.")
                return 0

            mouse.click_screen(point, hover_delay=0.0)
            if args.settle:
                time.sleep(args.settle)

            after = observer.observe()
            decoder, _, root = observer._root()
            try:
                _, after_area = _pack_area(decoder, root)
                after_cards = _pack_card_addresses(decoder, after_area)
                highlighted = _highlighted_addresses(decoder, after_area)
            except Exception:
                after_area = {}
                after_cards = []
                highlighted = {}

            target_still_present = card_address in after_cards
            markers_after: list[str] = []
            click_is_after = None
            if target_still_present:
                try:
                    after_card = decoder.string_fields(card_address)
                    markers_after = _selection_markers(decoder, after_card)
                    click_is_after = _state_flag(decoder, after_card, "click", "is")
                except Exception:
                    pass

            candidates, visited, _ = _scan_pack_controls(decoder, root)

            print("Mouse movement sent -> True")
            print("Mouse clicks sent -> True")
            print("Clicks sent -> 1")
            print(f"Phase after -> {after.phase}")
            print(f"State complete after -> {after.state_complete}")
            print(f"Pack card count after -> {len(after_cards)}")
            print(f"Clicked card still in G.pack_cards -> {target_still_present}")
            print(f"Clicked card states.click.is after -> {click_is_after!r}")
            print(f"Selection markers after -> {markers_after!r}")
            print(f"Highlighted arrays after -> {highlighted!r}")
            print(f"Post-click UI tables visited -> {visited}")
            print(f"Post-click pack/control candidates -> {len(candidates)}")
            for index, candidate in enumerate(candidates, start=1):
                print(f"  Candidate {index}: {candidate.path} @ 0x{candidate.address:x}")
                print("    match -> " + "; ".join(candidate.matches))
                print(f"    T -> {candidate.t}")
                print(f"    VT -> {candidate.vt}")
            return 0
    except Exception as error:
        print("Live pack card single-click probe -> FAIL")
        print(f"Reason -> {error}")
        print("Process writes/injection -> False")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
