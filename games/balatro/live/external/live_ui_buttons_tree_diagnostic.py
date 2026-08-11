from __future__ import annotations

from collections import deque

from .live_memory_observer import (
    LiveMemoryBalatroObserver,
    _geometry,
    _primitive,
)

MAX_DEPTH = 6
MAX_NODES = 800
INTERESTING_NAMES = {
    "button",
    "label",
    "text",
    "id",
    "name",
    "ref_table",
    "ref_value",
    "focus_args",
    "func",
    "callback",
    "action",
}


def _safe_fields(decoder, address: int) -> dict:
    try:
        return decoder.string_fields(address)
    except Exception:
        return {}


def _array_children(decoder, address: int) -> list[tuple[int, int]]:
    try:
        values = decoder.array_items(address)
    except Exception:
        return []
    return [
        (index, int(value.value))
        for index, value in values
        if value.kind == "table"
    ]


def _value_text(value) -> str | None:
    primitive = _primitive(value)
    if primitive is not None:
        return repr(primitive)
    if value.kind in {"function", "table", "userdata", "thread", "cdata"}:
        return f"{value.kind}@0x{int(value.value):x}"
    return None


def _node_summary(decoder, path: str, address: int, depth: int) -> list[str]:
    fields = _safe_fields(decoder, address)
    if not fields:
        return []

    geometry = _geometry(decoder, fields.get("T"))
    details: list[str] = []
    for name, value in sorted(fields.items()):
        lowered = name.casefold()
        text = _value_text(value)
        if text is None:
            continue
        primitive = _primitive(value)
        primitive_text = str(primitive).casefold() if primitive is not None else ""
        if (
            lowered in INTERESTING_NAMES
            or "button" in lowered
            or "play" in lowered
            or "discard" in lowered
            or "play" in primitive_text
            or "discard" in primitive_text
        ):
            details.append(f"{name}={text}")

    if not details and not geometry:
        return []

    lines = [f"{path} @ 0x{address:x} depth={depth}"]
    if details:
        lines.append("  fields -> " + "; ".join(details))
    if geometry:
        lines.append(
            "  T -> "
            + " ".join(
                f"{name}={geometry[name]:.6f}"
                for name in ("x", "y", "w", "h", "r", "scale")
                if name in geometry
            )
        )
    return lines


def main() -> int:
    try:
        with LiveMemoryBalatroObserver() as observer:
            decoder, _, root = observer._root()
            buttons = root.get("buttons")
            if buttons is None or buttons.kind != "table":
                raise RuntimeError("G.buttons is unavailable or not a table")

            root_address = int(buttons.value)
            queue = deque([("G.buttons", root_address, 0)])
            visited: set[int] = set()
            output: list[str] = []

            while queue and len(visited) < MAX_NODES:
                path, address, depth = queue.popleft()
                if address in visited:
                    continue
                visited.add(address)

                output.extend(_node_summary(decoder, path, address, depth))
                if depth >= MAX_DEPTH:
                    continue

                fields = _safe_fields(decoder, address)
                for name, value in sorted(fields.items()):
                    if value.kind == "table":
                        queue.append(
                            (f"{path}.{name}", int(value.value), depth + 1)
                        )
                for index, child in _array_children(decoder, address):
                    queue.append((f"{path}[{index + 1}]", child, depth + 1))
    except Exception as error:
        print("Live buttons tree diagnostic -> FAIL")
        print(f"Reason -> {error}")
        print("Mouse input sent -> False")
        return 2

    print("Live buttons tree diagnostic -> PASS")
    print("Observation source -> live Balatro process memory")
    print("Mouse input sent -> False")
    print("Process writes/injection -> False")
    print("Traversal root -> G.buttons only")
    print(f"Tables visited -> {len(visited)}")
    print(f"Relevant nodes printed -> {sum(1 for line in output if not line.startswith('  '))}")
    if output:
        for line in output:
            print(line)
    else:
        print("Relevant nodes -> none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
