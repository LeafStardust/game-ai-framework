from games.balatro.live.runtime import joker_generation_pool_observer as pool_observer
from games.balatro.live.runtime.luajit_memory import LuaJITMemoryError, LuaValue


def _table(address: int) -> LuaValue:
    return LuaValue("table", address, address)


def _string(value: str) -> LuaValue:
    return LuaValue("string", value, 0)


def _boolean(value: bool) -> LuaValue:
    return LuaValue("boolean", value, 0)


def _integer(value: int) -> LuaValue:
    return LuaValue("integer", value, 0)


class _Decoder:
    def __init__(self):
        self.fields: dict[int, dict[str, LuaValue]] = {}
        self.arrays: dict[int, tuple[tuple[int, LuaValue], ...]] = {}

    def array_items_strict(self, address: int):
        value = self.arrays.get(address)
        if isinstance(value, Exception):
            raise value
        if value is None:
            raise LuaJITMemoryError(f"missing array {address}")
        return value


def _install_strict_fields(monkeypatch, decoder: _Decoder):
    def _fields(_decoder, address):
        value = decoder.fields.get(address)
        if isinstance(value, Exception):
            raise value
        if value is None:
            raise LuaJITMemoryError(f"missing table {address}")
        return dict(value)

    monkeypatch.setattr(pool_observer, "string_fields_strict", _fields)


def _runtime(monkeypatch):
    decoder = _Decoder()
    _install_strict_fields(monkeypatch, decoder)

    decoder.fields[1] = {
        "used_jokers": _table(2),
        "pool_flags": _table(3),
        "banned_keys": _table(4),
    }
    decoder.fields[2] = {}
    decoder.fields[3] = {}
    decoder.fields[4] = {}

    decoder.fields[10] = {"cards": _table(11)}
    decoder.arrays[11] = ()

    decoder.arrays[20] = tuple((rarity, _table(20 + rarity)) for rarity in range(1, 5))

    center_ids = {
        1: (101, 102, 103),
        2: (201,),
        3: (301,),
        4: (401, 402),
    }
    keys = {
        101: "j_first",
        102: "j_second",
        103: "j_third",
        201: "j_uncommon",
        301: "j_rare",
        401: "j_legend_locked",
        402: "j_legend_open",
    }
    costs = {
        101: 2,
        102: 5,
        103: 7,
        201: 6,
        301: 8,
        401: 20,
        402: 20,
    }
    for rarity, ids in center_ids.items():
        decoder.arrays[20 + rarity] = tuple(
            (index, _table(center_id))
            for index, center_id in enumerate(ids, start=1)
        )
    for center_id, key in keys.items():
        decoder.fields[center_id] = {
            "key": _string(key),
            "cost": _integer(costs[center_id]),
        }

    root = {
        "GAME": _table(1),
        "jokers": _table(10),
        "P_JOKER_RARITY_POOLS": _table(20),
    }
    return decoder, root


def _keys(records):
    return [record["key"] for record in records]


def test_env_r2_live_joker_pool_preserves_runtime_rarity_order_and_public_record_shape(monkeypatch):
    decoder, root = _runtime(monkeypatch)
    decoder.fields[102]["unlocked"] = _boolean(True)
    decoder.fields[102]["no_pool_flag"] = _string("blocked")
    decoder.fields[102]["yes_pool_flag"] = _string("enabled")
    decoder.fields[3] = {"enabled": _boolean(True)}

    pools = pool_observer.observe_joker_generation_pools(decoder, root)

    assert pools is not None
    assert _keys(pools[1]) == ["j_first", "j_second", "j_third"]
    assert pools[1][1] == {
        "rarity": 1,
        "key": "j_second",
        "cost": 5,
        "unlocked": True,
        "no_pool_flag": "blocked",
        "yes_pool_flag": "enabled",
    }
    assert _keys(pools[2]) == ["j_uncommon"]
    assert _keys(pools[3]) == ["j_rare"]
    assert _keys(pools[4]) == ["j_legend_locked", "j_legend_open"]


def test_env_r2_live_joker_pool_applies_unlock_ban_and_pool_flags(monkeypatch):
    decoder, root = _runtime(monkeypatch)
    decoder.fields[101]["unlocked"] = _boolean(False)
    decoder.fields[102]["no_pool_flag"] = _string("blocked")
    decoder.fields[103]["yes_pool_flag"] = _string("enabled")
    decoder.fields[3] = {"blocked": _boolean(True), "enabled": _boolean(True)}
    decoder.fields[4] = {"j_uncommon": _boolean(True)}

    pools = pool_observer.observe_joker_generation_pools(decoder, root)

    assert pools is not None
    assert _keys(pools[1]) == ["j_third"]
    assert pools[2] == []


def test_env_r2_live_joker_pool_requires_yes_flag_and_legendary_ignores_unlock(monkeypatch):
    decoder, root = _runtime(monkeypatch)
    decoder.fields[101]["yes_pool_flag"] = _string("enabled")
    decoder.fields[401]["unlocked"] = _boolean(False)

    pools = pool_observer.observe_joker_generation_pools(decoder, root)

    assert pools is not None
    assert "j_first" not in _keys(pools[1])
    assert "j_legend_locked" in _keys(pools[4])
    locked_record = next(record for record in pools[4] if record["key"] == "j_legend_locked")
    assert locked_record["unlocked"] is False


def test_env_r2_live_joker_pool_suppresses_used_joker_without_showman(monkeypatch):
    decoder, root = _runtime(monkeypatch)
    decoder.fields[2] = {"j_second": _boolean(True)}

    pools = pool_observer.observe_joker_generation_pools(decoder, root)

    assert pools is not None
    assert _keys(pools[1]) == ["j_first", "j_third"]


def test_env_r2_live_joker_pool_allows_used_joker_with_showman(monkeypatch):
    decoder, root = _runtime(monkeypatch)
    decoder.fields[2] = {"j_second": _boolean(True)}
    decoder.arrays[11] = ((1, _table(50)),)
    decoder.fields[50] = {"config": _table(51)}
    decoder.fields[51] = {"center": _table(52)}
    decoder.fields[52] = {"key": _string("j_showman")}

    pools = pool_observer.observe_joker_generation_pools(decoder, root)

    assert pools is not None
    assert _keys(pools[1]) == ["j_first", "j_second", "j_third"]


def test_env_r2_live_joker_pool_fails_closed_on_incomplete_required_map(monkeypatch):
    decoder, root = _runtime(monkeypatch)
    decoder.fields[3] = LuaJITMemoryError("transient unreadable pool_flags")

    assert pool_observer.observe_joker_generation_pools(decoder, root) is None


def test_env_r2_live_joker_pool_fails_closed_on_malformed_center_metadata(monkeypatch):
    decoder, root = _runtime(monkeypatch)
    decoder.fields[101]["unlocked"] = _string("yes")

    assert pool_observer.observe_joker_generation_pools(decoder, root) is None
