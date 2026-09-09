"""Private live run facts used only for deterministic R5 replay fixtures."""

from __future__ import annotations

from games.balatro.live.runtime.luajit_memory import LuaJITMemoryError
from games.balatro.live.runtime.process_memory import BalatroProcessMemoryError


class LivePrivateRunStateError(RuntimeError):
    """Raised when private replay-only run state cannot be read exactly."""


def active_tag_count_from_live_memory(decoder, root) -> int:
    """Read the exact active `G.GAME.tags` length without exposing Tag identity."""
    game_value = root.get("GAME")
    if game_value is None or getattr(game_value, "kind", None) != "table":
        raise LivePrivateRunStateError("live Balatro G.GAME table is unavailable")
    try:
        game = decoder.string_fields(int(game_value.value))
    except (BalatroProcessMemoryError, LuaJITMemoryError, TypeError, ValueError) as exc:
        raise LivePrivateRunStateError("unable to read live Balatro G.GAME table") from exc

    tags_value = game.get("tags")
    if tags_value is None or getattr(tags_value, "kind", None) != "table":
        raise LivePrivateRunStateError("live Balatro G.GAME.tags table is unavailable")
    try:
        items = list(decoder.array_items(int(tags_value.value)))
    except (BalatroProcessMemoryError, LuaJITMemoryError, TypeError, ValueError) as exc:
        raise LivePrivateRunStateError("unable to read live Balatro active Tags") from exc
    for _, value in items:
        if value is None or getattr(value, "kind", None) != "table":
            raise LivePrivateRunStateError("live Balatro active Tag array is malformed")
    return len(items)
