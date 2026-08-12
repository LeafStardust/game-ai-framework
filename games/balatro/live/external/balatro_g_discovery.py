from __future__ import annotations

from .luajit_memory import LuaJITMemoryError, LuaValue
from .luajit_non_gc64_memory import LuaJITNonGC64Decoder
from .process_memory import BalatroProcessMemoryError


_REQUIRED_FIELDS = {
    "GAME": "table",
    "STATE": ("integer", "number"),
    "hand": "table",
    "jokers": "table",
}

_STRONG_TABLE_FIELDS = (
    "STATES",
    "consumeables",
    "deck",
)

_AREA_FIELDS = (
    "hand",
    "jokers",
    "consumeables",
    "deck",
)


def _kind_matches(value: LuaValue | None, expected) -> bool:
    if value is None:
        return False
    if isinstance(expected, tuple):
        return value.kind in expected
    return value.kind == expected


def _area_has_cards_table(
    decoder: LuaJITNonGC64Decoder,
    value: LuaValue | None,
) -> bool:
    if value is None or value.kind != "table":
        return False
    try:
        fields = decoder.string_fields(int(value.value))
    except (BalatroProcessMemoryError, LuaJITMemoryError):
        return False
    cards = fields.get("cards")
    return cards is not None and cards.kind == "table"


def _candidate_score(
    decoder: LuaJITNonGC64Decoder,
    table: int,
) -> tuple[int, tuple[str, ...]] | None:
    try:
        fields = decoder.string_fields(table)
    except (BalatroProcessMemoryError, LuaJITMemoryError):
        return None

    for name, expected in _REQUIRED_FIELDS.items():
        if not _kind_matches(fields.get(name), expected):
            return None

    score = 100
    evidence: list[str] = ["required-core"]

    for name in _STRONG_TABLE_FIELDS:
        value = fields.get(name)
        if value is not None and value.kind == "table":
            score += 10
            evidence.append(name)

    for name in _AREA_FIELDS:
        if _area_has_cards_table(decoder, fields.get(name)):
            score += 5
            evidence.append(f"{name}.cards")

    game = fields.get("GAME")
    if game is not None and game.kind == "table":
        try:
            game_fields = decoder.string_fields(int(game.value))
        except (BalatroProcessMemoryError, LuaJITMemoryError):
            game_fields = {}

        for name in ("current_round", "round_resets"):
            value = game_fields.get(name)
            if value is not None and value.kind == "table":
                score += 5
                evidence.append(f"GAME.{name}")

        dollars = game_fields.get("dollars")
        if dollars is not None and dollars.kind in {"integer", "number"}:
            score += 5
            evidence.append("GAME.dollars")

    return score, tuple(evidence)


def validate_balatro_g_table(
    decoder: LuaJITNonGC64Decoder,
    table: int,
) -> bool:
    """Return whether an already-known address still looks like Balatro's ``G``.

    This is intentionally structural rather than address-based. It lets callers
    safely reuse a previously discovered address without another whole-process
    scan, while still failing closed when the Lua VM or process has changed.
    """
    return _candidate_score(decoder, int(table)) is not None


def _rank_candidates(
    candidates: dict[int, tuple[int, tuple[str, ...]]],
    *,
    source: str,
) -> int | None:
    if not candidates:
        return None

    ranked = sorted(
        candidates.items(),
        key=lambda item: (-item[1][0], item[0]),
    )
    best_table, (best_score, _) = ranked[0]

    if len(ranked) > 1 and ranked[1][1][0] == best_score:
        details = ", ".join(
            f"0x{table:x}:score={score}"
            for table, (score, _) in ranked[:8]
        )
        raise LuaJITMemoryError(
            f"multiple equally strong Balatro G {source} candidates; {details}"
        )

    return best_table


def _discover_from_global_binding(
    decoder: LuaJITNonGC64Decoder,
) -> int | None:
    candidates: dict[int, tuple[int, tuple[str, ...]]] = {}

    for string_address in decoder.find_gc_strings("G", max_matches=64):
        for node in decoder.find_key_nodes_for_string(string_address):
            try:
                value = decoder.read_value_at(node)
            except (BalatroProcessMemoryError, LuaJITMemoryError):
                continue
            if value.kind != "table":
                continue

            table = int(value.value)
            validated = _candidate_score(decoder, table)
            if validated is None:
                continue

            previous = candidates.get(table)
            if previous is None or validated[0] > previous[0]:
                candidates[table] = validated

    return _rank_candidates(candidates, source="global-binding")


def _discover_from_game_owner(
    decoder: LuaJITNonGC64Decoder,
) -> int | None:
    """Recover ``G`` by finding the table that owns its ``GAME`` hash node."""

    candidates: dict[int, tuple[int, tuple[str, ...]]] = {}

    for string_address in decoder.find_gc_strings("GAME", max_matches=64):
        for node in decoder.find_key_nodes_for_string(string_address):
            try:
                value = decoder.read_value_at(node)
            except (BalatroProcessMemoryError, LuaJITMemoryError):
                continue
            if value.kind != "table":
                continue

            try:
                owners = decoder.find_table_owners_of_node(node)
            except (BalatroProcessMemoryError, LuaJITMemoryError):
                continue

            for table in owners:
                validated = _candidate_score(decoder, int(table))
                if validated is None:
                    continue

                previous = candidates.get(int(table))
                if previous is None or validated[0] > previous[0]:
                    candidates[int(table)] = validated

    return _rank_candidates(candidates, source="GAME-owner")


def discover_balatro_g_table(
    decoder: LuaJITNonGC64Decoder,
) -> int:
    """Discover Balatro's live global ``G`` with a structural fallback.

    The fast path resolves the Lua global binding named ``G`` directly. Some
    live LuaJIT layouts do not leave that binding discoverable through the
    interned-string reference scan, even though the table itself remains fully
    reachable. In that case, the fallback locates the ``GAME`` field node,
    reverse-maps it to candidate table owners, and applies the same Balatro-
    specific structural validation and ambiguity checks.
    """

    direct = _discover_from_global_binding(decoder)
    if direct is not None:
        return direct

    fallback = _discover_from_game_owner(decoder)
    if fallback is not None:
        return fallback

    raise LuaJITMemoryError(
        "unable to identify Balatro G from either the live Lua global binding "
        "or the structural GAME-owner fallback"
    )
