from games.balatro.live.runtime import consumable_generation_pool_observer as observer
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
        self.fields: dict[int, object] = {}
        self.arrays: dict[int, object] = {}

    def array_items_strict(self, address: int):
        value = self.arrays.get(address)
        if isinstance(value, Exception):
            raise value
        if value is None:
            raise LuaJITMemoryError(f"missing array {address}")
        return value


def _install_fields(monkeypatch, decoder: _Decoder):
    def _fields(_decoder, address):
        value = decoder.fields.get(address)
        if isinstance(value, Exception):
            raise value
        if value is None:
            raise LuaJITMemoryError(f"missing table {address}")
        return dict(value)

    monkeypatch.setattr(
        "games.balatro.live.runtime.joker_generation_pool_observer.string_fields_strict",
        _fields,
    )


def _runtime(monkeypatch):
    decoder = _Decoder()
    _install_fields(monkeypatch, decoder)

    decoder.fields[1] = {
        "used_jokers": _table(2),
        "pool_flags": _table(3),
        "banned_keys": _table(4),
        "hands": _table(5),
    }
    decoder.fields[2] = {}
    decoder.fields[3] = {}
    decoder.fields[4] = {}
    decoder.fields[5] = {
        "High Card": _table(51),
        "Five of a Kind": _table(52),
    }
    decoder.fields[51] = {"played": _integer(2)}
    decoder.fields[52] = {"played": _integer(0)}

    decoder.fields[10] = {"cards": _table(11)}
    decoder.arrays[11] = ()

    decoder.fields[20] = {"Tarot": _table(21), "Planet": _table(22)}
    decoder.arrays[21] = ((1, _table(101)), (2, _table(102)))
    decoder.arrays[22] = ((1, _table(201)), (2, _table(202)))

    decoder.fields[101] = {"key": _string("c_fool"), "cost": _integer(3)}
    decoder.fields[102] = {"key": _string("c_strength"), "cost": _integer(3)}
    decoder.fields[201] = {
        "key": _string("c_pluto"),
        "cost": _integer(3),
        "config": _table(211),
    }
    decoder.fields[211] = {
        "softlock": _boolean(False),
        "hand_type": _string("High Card"),
    }
    decoder.fields[202] = {
        "key": _string("c_planet_x"),
        "cost": _integer(3),
        "config": _table(212),
    }
    decoder.fields[212] = {
        "softlock": _boolean(True),
        "hand_type": _string("Five of a Kind"),
    }

    root = {
        "GAME": _table(1),
        "jokers": _table(10),
        "P_CENTER_POOLS": _table(20),
    }
    return decoder, root


def _keys(records):
    return [record["key"] for record in records]


def test_env_r2_live_consumable_pool_applies_planet_softlock(monkeypatch):
    decoder, root = _runtime(monkeypatch)

    pools = observer.observe_consumable_generation_pools(decoder, root)

    assert pools is not None
    assert _keys(pools["Tarot"]) == ["c_fool", "c_strength"]
    assert _keys(pools["Planet"]) == ["c_pluto"]
    assert pools["Planet"][0]["cost"] == 3
    assert pools["Planet"][0]["softlock"] is False


def test_env_r2_live_consumable_pool_unlocks_softlocked_planet_after_hand_play(monkeypatch):
    decoder, root = _runtime(monkeypatch)
    decoder.fields[52] = {"played": _integer(1)}

    pools = observer.observe_consumable_generation_pools(decoder, root)

    assert pools is not None
    assert _keys(pools["Planet"]) == ["c_pluto", "c_planet_x"]
    assert pools["Planet"][1]["hand_type"] == "Five of a Kind"


def test_env_r2_live_consumable_pool_applies_duplicate_ban_and_flags(monkeypatch):
    decoder, root = _runtime(monkeypatch)
    decoder.fields[2] = {"c_fool": _boolean(True)}
    decoder.fields[4] = {"c_pluto": _boolean(True)}
    decoder.fields[102]["yes_pool_flag"] = _string("tarot_enabled")

    pools = observer.observe_consumable_generation_pools(decoder, root)
    assert pools is not None
    assert pools["Tarot"] == []
    assert pools["Planet"] == []

    decoder.fields[3] = {"tarot_enabled": _boolean(True)}
    pools = observer.observe_consumable_generation_pools(decoder, root)
    assert pools is not None
    assert _keys(pools["Tarot"]) == ["c_strength"]


def test_env_r2_live_consumable_pool_showman_overrides_used_center(monkeypatch):
    decoder, root = _runtime(monkeypatch)
    decoder.fields[2] = {"c_fool": _boolean(True)}
    decoder.arrays[11] = ((1, _table(60)),)
    decoder.fields[60] = {"config": _table(61)}
    decoder.fields[61] = {"center": _table(62)}
    decoder.fields[62] = {"key": _string("j_showman")}

    pools = observer.observe_consumable_generation_pools(decoder, root)

    assert pools is not None
    assert "c_fool" in _keys(pools["Tarot"])


def test_env_r2_live_consumable_pool_fails_closed_on_incomplete_metadata(monkeypatch):
    decoder, root = _runtime(monkeypatch)
    decoder.fields[101].pop("cost")

    assert observer.observe_consumable_generation_pools(decoder, root) is None

    decoder, root = _runtime(monkeypatch)
    decoder.fields[212]["softlock"] = _string("yes")
    assert observer.observe_consumable_generation_pools(decoder, root) is None
