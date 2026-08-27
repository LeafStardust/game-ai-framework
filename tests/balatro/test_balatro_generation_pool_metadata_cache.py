from types import SimpleNamespace

import games.balatro.consumable_generation_pool_live_state_policy as consumable_pool
import games.balatro.joker_generation_pool_live_state_policy as joker_pool


class _Decoder:
    def __init__(self):
        self.calls = 0

    def string_fields(self, pointer):
        self.calls += 1
        return {"key": f"center-{pointer}", "name": f"Center {pointer}"}


def _table(pointer):
    return SimpleNamespace(kind="table", value=pointer)


def _exercise(module):
    module._CENTER_FIELDS_CACHE.clear()
    module._CENTER_CACHE_POOL_POINTER = None
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
    _exercise(joker_pool)


def test_consumable_generation_catalogue_reuses_static_center_decode():
    _exercise(consumable_pool)
