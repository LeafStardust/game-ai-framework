from __future__ import annotations

import json
from types import SimpleNamespace

from games.balatro.live.external import balatro_g_discovery as discovery
from games.balatro.live.external.luajit_memory import LuaJITMemoryError, LuaValue


def _table(address: int) -> LuaValue:
    return LuaValue("table", address, 0)


def _integer(value: int) -> LuaValue:
    return LuaValue("integer", value, 0)


def _valid_tables(g_table: int = 100) -> dict[int, dict[str, LuaValue]]:
    game = 200
    hand = 300
    jokers = 301
    states = 302
    consumables = 303
    deck = 304
    return {
        g_table: {
            "GAME": _table(game),
            "STATE": _integer(1),
            "hand": _table(hand),
            "jokers": _table(jokers),
            "STATES": _table(states),
            "consumeables": _table(consumables),
            "deck": _table(deck),
        },
        game: {
            "current_round": _table(400),
            "round_resets": _table(401),
            "dollars": _integer(7),
        },
        hand: {"cards": _table(500)},
        jokers: {"cards": _table(501)},
        consumables: {"cards": _table(502)},
        deck: {"cards": _table(503)},
        states: {},
        400: {},
        401: {},
        500: {},
        501: {},
        502: {},
        503: {},
    }


class FakeDecoder:
    POINTER_MASK = 0xFFFFFFFF

    def __init__(self, *, pid: int, tables=None):
        self.reader = SimpleNamespace(pid=pid)
        self.tables = tables or _valid_tables()

    def string_fields(self, address: int):
        try:
            return self.tables[address]
        except KeyError as error:
            raise LuaJITMemoryError(f"unknown fake table 0x{address:x}") from error


def test_discovery_cache_reuses_valid_address_for_same_pid(tmp_path, monkeypatch):
    cache_path = tmp_path / "balatro-g.json"
    monkeypatch.setattr(discovery, "_g_cache_path", lambda pid: cache_path)

    first = FakeDecoder(pid=1234)
    calls = []
    monkeypatch.setattr(
        discovery,
        "_discover_from_global_binding",
        lambda decoder: calls.append("discover") or 100,
    )
    monkeypatch.setattr(
        discovery,
        "_discover_from_game_owner",
        lambda decoder: (_ for _ in ()).throw(AssertionError("fallback not expected")),
    )

    assert discovery.discover_balatro_g_table(first) == 100
    assert first.g_table_cache_hit is False
    assert calls == ["discover"]
    assert cache_path.exists()

    second = FakeDecoder(pid=1234)
    monkeypatch.setattr(
        discovery,
        "_discover_from_global_binding",
        lambda decoder: (_ for _ in ()).throw(AssertionError("cache should avoid scan")),
    )

    assert discovery.discover_balatro_g_table(second) == 100
    assert second.g_table_cache_hit is True


def test_discovery_cache_rejects_pid_mismatch(tmp_path, monkeypatch):
    cache_path = tmp_path / "balatro-g.json"
    cache_path.write_text(
        json.dumps({"version": 1, "pid": 111, "g_table": 100}),
        encoding="utf-8",
    )
    monkeypatch.setattr(discovery, "_g_cache_path", lambda pid: cache_path)

    decoder = FakeDecoder(pid=222)
    calls = []
    monkeypatch.setattr(
        discovery,
        "_discover_from_global_binding",
        lambda current: calls.append("discover") or 100,
    )
    monkeypatch.setattr(discovery, "_discover_from_game_owner", lambda current: None)

    assert discovery.discover_balatro_g_table(decoder) == 100
    assert decoder.g_table_cache_hit is False
    assert calls == ["discover"]


def test_discovery_cache_rejects_invalid_cached_address(tmp_path, monkeypatch):
    cache_path = tmp_path / "balatro-g.json"
    cache_path.write_text(
        json.dumps({"version": 1, "pid": 333, "g_table": 999}),
        encoding="utf-8",
    )
    monkeypatch.setattr(discovery, "_g_cache_path", lambda pid: cache_path)

    decoder = FakeDecoder(pid=333)
    calls = []
    monkeypatch.setattr(
        discovery,
        "_discover_from_global_binding",
        lambda current: calls.append("discover") or 100,
    )
    monkeypatch.setattr(discovery, "_discover_from_game_owner", lambda current: None)

    assert discovery.discover_balatro_g_table(decoder) == 100
    assert decoder.g_table_cache_hit is False
    assert calls == ["discover"]
