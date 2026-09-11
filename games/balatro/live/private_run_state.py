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


def physical_draw_pile_live_ids_from_live_memory(decoder, root) -> tuple[int, ...]:
    """Read private ``G.deck.cards`` order as exact permanent card IDs.

    The tuple follows Balatro's physical CardArea array order; its final element
    is the next ordinary draw. This replay-only authority must never enter the
    public snapshot or policy observation.
    """
    deck_value = root.get("deck")
    if deck_value is None or getattr(deck_value, "kind", None) != "table":
        raise LivePrivateRunStateError("live Balatro G.deck table is unavailable")
    try:
        deck = decoder.string_fields(int(deck_value.value))
    except (BalatroProcessMemoryError, LuaJITMemoryError, TypeError, ValueError) as exc:
        raise LivePrivateRunStateError("unable to read live Balatro G.deck table") from exc

    cards_value = deck.get("cards")
    if cards_value is None or getattr(cards_value, "kind", None) != "table":
        raise LivePrivateRunStateError("live Balatro G.deck.cards table is unavailable")
    try:
        items = list(decoder.array_items_strict(int(cards_value.value)))
    except (BalatroProcessMemoryError, LuaJITMemoryError, TypeError, ValueError) as exc:
        raise LivePrivateRunStateError("unable to read live Balatro physical draw pile") from exc
    # Lua's sequence keys are one-based. The decoder reports the physical array
    # slot/key unchanged, so an exact dense CardArea is 1..N (slot 0 is nil).
    if [index for index, _ in items] != list(range(1, len(items) + 1)):
        raise LivePrivateRunStateError(
            "live Balatro physical draw-pile array is not contiguous"
        )

    live_ids: list[int] = []
    for _, card_value in items:
        if card_value is None or getattr(card_value, "kind", None) != "table":
            raise LivePrivateRunStateError(
                "live Balatro physical draw-pile card is malformed"
            )
        try:
            card = decoder.string_fields(int(card_value.value))
        except (BalatroProcessMemoryError, LuaJITMemoryError, TypeError, ValueError) as exc:
            raise LivePrivateRunStateError(
                "unable to read live Balatro physical draw-pile card"
            ) from exc
        value = card.get("playing_card")
        if value is None or getattr(value, "kind", None) not in {"integer", "number"}:
            raise LivePrivateRunStateError(
                "live Balatro physical draw-pile card has no exact live ID"
            )
        live_id = value.value
        if (
            isinstance(live_id, bool)
            or not isinstance(live_id, (int, float))
            or (isinstance(live_id, float) and not live_id.is_integer())
            or int(live_id) < 0
        ):
            raise LivePrivateRunStateError(
                "live Balatro physical draw-pile card has invalid live ID"
            )
        live_ids.append(int(live_id))
    if len(set(live_ids)) != len(live_ids):
        raise LivePrivateRunStateError(
            "live Balatro physical draw-pile card IDs are not unique"
        )
    return tuple(live_ids)
