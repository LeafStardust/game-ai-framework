from types import SimpleNamespace

import games.balatro.consumable_generation_pool_live_state_policy as consumable_pool
import games.balatro.joker_generation_pool_live_state_policy as joker_pool


class _Decoder:
    def __init__(self, arrays=None):
        self.calls = 0
        self.array_calls = 0
        self.arrays = dict(arrays or {})

    def string_fields(self, pointer):
        self.calls += 1
        return {"key": f"center-{pointer}", "name": f"Center {pointer}"}

    def array_items(self, pointer):
        self.array_calls += 1
        return list(self.arrays.get(pointer, ()))


def _table(pointer):
    return SimpleNamespace(kind="table", value=pointer)


def _exercise_center_cache(module):
    module._reset_catalogue_cache()
    decoder = _Decoder()

    module._prepare_center_cache(_table(100))
    first = module._center_fields(decoder, 200)
    second = module._center_fields(decoder, 200)

    assert first == second
    assert decoder.calls == 1

    module._prepare_center_cache(_table(101))
    third = module._center_fields(decoder, 200)

    assert third == first
    assert decoder.calls == 2


def test_joker_generation_catalogue_reuses_static_center_decode():
    _exercise_center_cache(joker_pool)


def test_consumable_generation_catalogue_reuses_static_center_decode():
    _exercise_center_cache(consumable_pool)


def test_joker_generation_catalogue_reuses_rarity_pool_enumeration():
    joker_pool._reset_catalogue_cache()
    decoder = _Decoder(
        {
            100: ((1, _table(101)), (2, _table(102)), (3, _table(103))),
            101: ((1, _table(201)),),
            102: ((1, _table(202)),),
            103: ((1, _table(203)),),
        }
    )

    first, first_complete = joker_pool._rarity_catalogue(decoder, _table(100))
    first_array_calls = decoder.array_calls
    first_center_calls = decoder.calls
    second, second_complete = joker_pool._rarity_catalogue(decoder, _table(100))

    assert first_complete is True
    assert second_complete is True
    assert second == first
    assert first_array_calls == 4
    assert decoder.array_calls == first_array_calls
    assert first_center_calls == 3
    assert decoder.calls == first_center_calls


def test_consumable_generation_catalogue_reuses_pool_enumeration(monkeypatch):
    consumable_pool._reset_catalogue_cache()
    decoder = _Decoder(
        {
            101: ((1, _table(201)),),
            102: ((1, _table(202)),),
        }
    )

    original_table_fields = consumable_pool.live_memory_observer._table_fields

    def table_fields(current_decoder, value):
        if value is not None and getattr(value, "kind", None) == "table" and int(value.value) == 100:
            return {"Tarot": _table(101), "Spectral": _table(102)}
        return original_table_fields(current_decoder, value)

    monkeypatch.setattr(consumable_pool.live_memory_observer, "_table_fields", table_fields)

    first, first_complete = consumable_pool._pool_catalogue(decoder, _table(100))
    first_array_calls = decoder.array_calls
    first_center_calls = decoder.calls
    second, second_complete = consumable_pool._pool_catalogue(decoder, _table(100))

    assert first_complete is True
    assert second_complete is True
    assert second == first
    assert first_array_calls == 2
    assert decoder.array_calls == first_array_calls
    assert first_center_calls == 2
    assert decoder.calls == first_center_calls
