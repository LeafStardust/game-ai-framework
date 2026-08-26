from __future__ import annotations

"""Expose Balatro's current public Tarot/Spectral generation pools.

Arcana and generated-consumable expectations need the same catalogue Balatro's
``get_current_pool`` would use, but never its pseudoseed, pool order, or selected
future result. This adapter therefore exports only currently eligible center
records after ordinary public culling: unlock state, duplicate exclusion unless
Showman is owned, challenge bans, and pool flags. The normal-pool exclusions for
The Soul and Black Hole are mirrored exactly, as are Balatro's Strength/Incantation
empty-pool fallbacks.

Omen Globe's redeemed bit is exported alongside the pools because it changes each
Arcana offer from Tarot-only to an explicit 80% Tarot / 20% Spectral mixture. Soul
and Black Hole eligibility are also exported because ``create_card(..., soulable)``
has an exact 0.3% special override before ordinary pool selection. These are
ordinary public run-state predicates, not RNG state or future-result information.
"""

from games.balatro.live.runtime import live_memory_observer
from games.balatro.live.translator import DefaultBalatroStateTranslator
from games.balatro.state import BalatroState


_POOL_SPECS = {
    "TAROT": ("Tarot", "c_strength"),
    "SPECTRAL": ("Spectral", "c_incantation"),
}


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


def _special_available(
    *,
    key: str,
    used: dict,
    banned: dict,
    showman: bool,
) -> bool:
    if _bool_field(banned, key, False):
        return False
    if not showman and _bool_field(used, key, False):
        return False
    return True


def _normalize_consumable_generation_pools(decoder, root, payload):
    outer = live_memory_observer._table_fields(decoder, root.get("P_CENTER_POOLS"))
    game = live_memory_observer._table_fields(decoder, root.get("GAME"))
    used = live_memory_observer._table_fields(decoder, game.get("used_jokers"))
    banned = live_memory_observer._table_fields(decoder, game.get("banned_keys"))
    pool_flags = live_memory_observer._table_fields(decoder, game.get("pool_flags"))
    showman = _showman_owned(payload)

    complete = True
    result: dict[str, list[dict]] = {}

    for public_name, (pool_name, fallback_key) in _POOL_SPECS.items():
        pool_value = outer.get(pool_name)
        if pool_value is None or getattr(pool_value, "kind", None) != "table":
            result[public_name] = []
            complete = False
            continue

        records: list[dict] = []
        all_records: dict[str, dict] = {}
        for _, center_value in _table_items(decoder, pool_value):
            if getattr(center_value, "kind", None) != "table":
                continue
            try:
                center = decoder.string_fields(int(center_value.value))
            except (
                live_memory_observer.BalatroProcessMemoryError,
                live_memory_observer.LuaJITMemoryError,
                TypeError,
                ValueError,
            ):
                complete = False
                continue

            key = live_memory_observer._string(center.get("key"))
            label = live_memory_observer._string(center.get("name"))
            if not key or not label:
                complete = False
                continue

            record = {
                "center": key,
                "label": label,
                "ability_name": label,
                "ability_set": public_name,
            }
            all_records[key] = record

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

            # get_current_pool removes these from the ordinary Spectral pool; they
            # are injected only by create_card's separate soulable branch.
            if public_name == "SPECTRAL" and label in {"Black Hole", "The Soul"}:
                continue

            records.append(record)

        if not records:
            fallback = all_records.get(fallback_key)
            if fallback is None:
                complete = False
            else:
                records = [fallback]

        records.sort(key=lambda record: (str(record.get("center")), str(record.get("label"))))
        result[public_name] = records

    used_vouchers = live_memory_observer._table_fields(decoder, game.get("used_vouchers"))
    omen_globe = _bool_field(used_vouchers, "v_omen_globe", False)
    soul_available = _special_available(
        key="c_soul",
        used=used,
        banned=banned,
        showman=showman,
    )
    black_hole_available = _special_available(
        key="c_black_hole",
        used=used,
        banned=banned,
        showman=showman,
    )
    return (
        result,
        complete,
        omen_globe,
        showman,
        soul_available,
        black_hole_available,
    )


def install_consumable_generation_pool_live_state_policy() -> None:
    if getattr(DefaultBalatroStateTranslator, "_consumable_generation_pool_live_state_installed", False):
        return

    original_snapshot_payload = live_memory_observer.snapshot_payload_from_live_memory
    original_translate = DefaultBalatroStateTranslator.translate
    original_state_init = BalatroState.__init__
    original_state_copy = BalatroState.copy

    def state_init(self):
        original_state_init(self)
        self.consumable_generation_pool_observed = False
        self.consumable_generation_pools = {}
        self.omen_globe_active = False
        self.consumable_generation_showman = False
        self.soul_generation_available = False
        self.black_hole_generation_available = False

    def state_copy(self):
        copied = original_state_copy(self)
        copied.consumable_generation_pool_observed = bool(
            getattr(self, "consumable_generation_pool_observed", False)
        )
        copied.consumable_generation_pools = {
            str(kind): [dict(record) for record in records]
            for kind, records in dict(getattr(self, "consumable_generation_pools", {}) or {}).items()
            if isinstance(records, (list, tuple))
        }
        copied.omen_globe_active = bool(getattr(self, "omen_globe_active", False))
        copied.consumable_generation_showman = bool(
            getattr(self, "consumable_generation_showman", False)
        )
        copied.soul_generation_available = bool(
            getattr(self, "soul_generation_available", False)
        )
        copied.black_hole_generation_available = bool(
            getattr(self, "black_hole_generation_available", False)
        )
        return copied

    def snapshot_payload_from_live_memory(decoder, root):
        payload, phase, state_complete = original_snapshot_payload(decoder, root)
        (
            pools,
            complete,
            omen_globe,
            showman,
            soul_available,
            black_hole_available,
        ) = _normalize_consumable_generation_pools(decoder, root, payload)
        payload["consumable_generation_pool_observed"] = bool(complete)
        payload["consumable_generation_pools"] = pools
        payload["omen_globe_active"] = bool(omen_globe)
        payload["consumable_generation_showman"] = bool(showman)
        payload["soul_generation_available"] = bool(soul_available)
        payload["black_hole_generation_available"] = bool(black_hole_available)
        return payload, phase, state_complete

    def translate(self, snapshot):
        state = original_translate(self, snapshot)
        payload = snapshot.payload
        pools = payload.get("consumable_generation_pools")
        state.consumable_generation_pool_observed = bool(
            payload.get("consumable_generation_pool_observed", False)
        )
        state.consumable_generation_pools = (
            {
                str(kind).upper(): [dict(record) for record in records if isinstance(record, dict)]
                for kind, records in pools.items()
                if isinstance(records, list)
            }
            if isinstance(pools, dict)
            else {}
        )
        state.omen_globe_active = bool(payload.get("omen_globe_active", False))
        state.consumable_generation_showman = bool(
            payload.get("consumable_generation_showman", False)
        )
        state.soul_generation_available = bool(
            payload.get("soul_generation_available", False)
        )
        state.black_hole_generation_available = bool(
            payload.get("black_hole_generation_available", False)
        )
        return state

    BalatroState.__init__ = state_init
    BalatroState.copy = state_copy
    live_memory_observer.snapshot_payload_from_live_memory = snapshot_payload_from_live_memory
    DefaultBalatroStateTranslator.translate = translate
    DefaultBalatroStateTranslator._consumable_generation_pool_live_state_installed = True
