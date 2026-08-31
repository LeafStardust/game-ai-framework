from __future__ import annotations

"""Read the public live Joker-generation catalogue without exposing RNG state."""

from games.balatro.live.runtime import live_memory_observer


_RARITY_NAMES = {1: "COMMON", 2: "UNCOMMON", 3: "RARE"}
_CENTER_FIELDS_CACHE: dict[int, dict] = {}
_CENTER_CACHE_POOL_POINTER: int | None = None
_RARITY_CATALOGUE_CACHE: dict[str, tuple[dict, ...]] = {}


def _table_items(decoder, table_value):
    if table_value is None or getattr(table_value, "kind", None) != "table":
        return []
    try:
        return list(decoder.array_items(int(table_value.value)))
    except (
        live_memory_observer.BalatroProcessMemoryError,
        live_memory_observer.LuaJITMemoryError,
        TypeError,
        ValueError,
    ):
        return []


def _bool_field(fields: dict, key: str, default: bool = False) -> bool:
    return live_memory_observer._boolean(fields.get(key), default)


def _showman_owned(payload: dict) -> bool:
    area = payload.get("jokers")
    cards = area.get("cards") if isinstance(area, dict) else None
    if not isinstance(cards, list):
        return False
    return any(
        isinstance(card, dict) and str(card.get("center") or "") == "j_showman"
        for card in cards
    )


def _owned_enhancement_centers(payload: dict) -> set[str] | None:
    area = payload.get("owned_cards")
    if not isinstance(area, dict):
        return None
    cards = area.get("cards")
    if not isinstance(cards, list):
        return None
    return {
        str(card.get("center"))
        for card in cards
        if isinstance(card, dict) and str(card.get("center") or "").startswith("m_")
    }


def _visible_poker_hands(decoder, game: dict) -> tuple[str, ...]:
    hands = live_memory_observer._table_fields(decoder, game.get("hands"))
    visible: list[str] = []
    for name, value in hands.items():
        hand = live_memory_observer._table_fields(decoder, value)
        if _bool_field(hand, "visible", False):
            visible.append(str(name))
    return tuple(sorted(visible))


def _prepare_center_cache(pools_value) -> None:
    global _CENTER_CACHE_POOL_POINTER
    try:
        pool_pointer = (
            int(pools_value.value)
            if pools_value is not None and getattr(pools_value, "kind", None) == "table"
            else None
        )
    except (TypeError, ValueError):
        pool_pointer = None
    if pool_pointer != _CENTER_CACHE_POOL_POINTER:
        _CENTER_FIELDS_CACHE.clear()
        _RARITY_CATALOGUE_CACHE.clear()
        _CENTER_CACHE_POOL_POINTER = pool_pointer


def reset_catalogue_cache() -> None:
    global _CENTER_CACHE_POOL_POINTER
    _CENTER_FIELDS_CACHE.clear()
    _RARITY_CATALOGUE_CACHE.clear()
    _CENTER_CACHE_POOL_POINTER = None


def _center_fields(decoder, center_pointer: int) -> dict:
    cached = _CENTER_FIELDS_CACHE.get(int(center_pointer))
    if cached is not None:
        return cached
    fields = decoder.string_fields(int(center_pointer))
    _CENTER_FIELDS_CACHE[int(center_pointer)] = fields
    return fields


def _rarity_catalogue(decoder, pools_value) -> tuple[dict[str, tuple[dict, ...]], bool]:
    _prepare_center_cache(pools_value)
    if _RARITY_CATALOGUE_CACHE:
        return _RARITY_CATALOGUE_CACHE, True

    outer = [
        value
        for _, value in _table_items(decoder, pools_value)
        if getattr(value, "kind", None) == "table"
    ]
    if len(outer) < 3:
        return {}, False

    complete = True
    catalogue: dict[str, tuple[dict, ...]] = {}
    for rarity_number, rarity_table in enumerate(outer[:3], start=1):
        rarity_name = _RARITY_NAMES[rarity_number]
        centers: list[dict] = []
        for _, center_value in _table_items(decoder, rarity_table):
            if getattr(center_value, "kind", None) != "table":
                continue
            try:
                centers.append(_center_fields(decoder, int(center_value.value)))
            except (
                live_memory_observer.BalatroProcessMemoryError,
                live_memory_observer.LuaJITMemoryError,
                TypeError,
                ValueError,
            ):
                complete = False
        catalogue[rarity_name] = tuple(centers)

    if complete:
        _RARITY_CATALOGUE_CACHE.update(catalogue)
    return catalogue, complete


def observe_joker_generation_state(decoder, root, payload: dict, phase: str) -> dict:
    pools_value = root.get("P_JOKER_RARITY_POOLS")
    catalogue, complete = _rarity_catalogue(decoder, pools_value)
    result: dict[str, object] = {
        "joker_generation_pool_observed": False,
        "joker_generation_pools": {},
        "joker_generation_edition_rate": 1.0,
        "visible_poker_hands": [],
    }

    game = live_memory_observer._table_fields(decoder, root.get("GAME"))
    edition_rate = live_memory_observer._number(game.get("edition_rate"))
    result["joker_generation_edition_rate"] = max(
        0.0,
        float(edition_rate if edition_rate is not None else 1.0),
    )
    result["visible_poker_hands"] = list(_visible_poker_hands(decoder, game))

    if catalogue:
        used = live_memory_observer._table_fields(decoder, game.get("used_jokers"))
        banned = live_memory_observer._table_fields(decoder, game.get("banned_keys"))
        pool_flags = live_memory_observer._table_fields(decoder, game.get("pool_flags"))
        current_round = live_memory_observer._table_fields(decoder, game.get("current_round"))
        round_state = live_memory_observer._normalize_round_joker_public_state(decoder, current_round)
        showman = _showman_owned(payload)
        enhancement_centers = _owned_enhancement_centers(payload)
        pools: dict[str, list[dict]] = {}

        for rarity_number in range(1, 4):
            rarity_name = _RARITY_NAMES[rarity_number]
            records: list[dict] = []
            for center in catalogue.get(rarity_name, ()):
                key = live_memory_observer._string(center.get("key"))
                label = live_memory_observer._string(center.get("name"))
                if not key or not label:
                    complete = False
                    continue
                if not _bool_field(center, "unlocked", True):
                    continue
                if not showman and _bool_field(used, key, False):
                    continue
                if _bool_field(banned, key, False):
                    continue

                no_pool_flag = live_memory_observer._string(center.get("no_pool_flag"))
                if no_pool_flag and _bool_field(pool_flags, no_pool_flag, False):
                    continue
                yes_pool_flag = live_memory_observer._string(center.get("yes_pool_flag"))
                if yes_pool_flag and not _bool_field(pool_flags, yes_pool_flag, False):
                    continue

                enhancement_gate = live_memory_observer._string(center.get("enhancement_gate"))
                if enhancement_gate:
                    if enhancement_centers is None:
                        complete = False
                        continue
                    if enhancement_gate not in enhancement_centers:
                        continue

                record = {
                    "center": key,
                    "label": label,
                    "ability_name": label,
                    "ability_set": "JOKER",
                    "rarity": rarity_name,
                }
                public_state = round_state.get(key)
                if isinstance(public_state, dict) and public_state:
                    record["public_state"] = dict(public_state)
                records.append(record)

            records.sort(key=lambda record: (str(record.get("center")), str(record.get("label"))))
            pools[rarity_name] = records

        result["joker_generation_pool_observed"] = bool(complete)
        result["joker_generation_pools"] = pools

    if str(phase) == "GAME_OVER":
        reset_catalogue_cache()

    return result
