from __future__ import annotations

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _geometry,
    _number,
    _table_fields,
)
from .window import BalatroWindowLocator


def _fmt_geometry(value: dict[str, float]) -> str:
    if not value:
        return "missing"
    fields = []
    for key in ("x", "y", "w", "h", "r", "scale"):
        if key in value:
            fields.append(f"{key}={value[key]:.6f}")
    return " ".join(fields)


def main() -> int:
    try:
        window = BalatroWindowLocator().find()
        with LiveMemoryBalatroObserver() as observer:
            decoder, _, root = observer._root()
            snapshot = observer.observe()

            room = _table_fields(decoder, root.get("ROOM"))
            room_attach = _table_fields(decoder, root.get("ROOM_ATTACH"))
            hand = _table_fields(decoder, root.get("hand"))

            tile_w = _number(root.get("TILE_W"))
            tile_h = _number(root.get("TILE_H"))
            room_t = _geometry(decoder, room.get("T"))
            room_attach_t = _geometry(decoder, room_attach.get("T"))
            hand_t = _geometry(decoder, hand.get("T"))
    except Exception as error:
        print("Live UI geometry validation -> FAIL")
        print(f"Reason -> {error}")
        return 2

    rect = window.client_rect
    print("Live UI geometry validation -> PASS")
    print("Observation source -> live Balatro process memory")
    print("Mouse input sent -> False")
    print("Process writes/injection -> False")
    print(
        "Balatro client rect -> "
        f"left={rect.left} top={rect.top} width={rect.width} height={rect.height}"
    )
    print(f"G.TILE_W -> {tile_w}")
    print(f"G.TILE_H -> {tile_h}")
    print(f"G.ROOM.T -> {_fmt_geometry(room_t)}")
    print(f"G.ROOM_ATTACH.T -> {_fmt_geometry(room_attach_t)}")
    print(f"G.hand.T -> {_fmt_geometry(hand_t)}")

    hand_cards = (snapshot.payload.get("hand") or {}).get("cards") or []
    print(f"Hand cards -> {len(hand_cards)}")
    for index, card in enumerate(hand_cards):
        value = card.get("value") or {}
        ui = card.get("ui") or {}
        print(
            f"  H{index}: {value.get('rank')} / {value.get('suit')} "
            f"live_id={card.get('live_id')} T[{_fmt_geometry(ui)}]"
        )

    missing = [
        index
        for index, card in enumerate(hand_cards)
        if not (card.get("ui") or {}).get("w")
        or not (card.get("ui") or {}).get("h")
    ]
    if missing:
        print("Geometry completeness -> FAIL")
        print("Missing card geometry indices -> " + ",".join(map(str, missing)))
        return 2

    print("Geometry completeness -> PASS")
    print("Coordinate transform -> NOT_YET_VALIDATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
