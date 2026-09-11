import pytest

from games.balatro.live.private_run_state import (
    LivePrivateRunStateError,
    physical_draw_pile_live_ids_from_live_memory,
)
from games.balatro.live.runtime.luajit_memory import LuaValue


def _lua(kind, value):
    return LuaValue(kind=kind, value=value, raw=0)


class _Decoder:
    def __init__(self, *, indices=(1, 2, 3), live_ids=(8.0, 3, 11.0)):
        self.tables = {
            10: {"cards": _lua("table", 20)},
            **{
                100 + index: {"playing_card": _lua("number", live_id)}
                for index, live_id in enumerate(live_ids)
            },
        }
        self.items = [
            (array_index, _lua("table", 100 + index))
            for index, array_index in enumerate(indices)
        ]

    def string_fields(self, address):
        return dict(self.tables[address])

    def array_items_strict(self, address):
        assert address == 20
        return list(self.items)


def test_env_r5_private_draw_order_preserves_physical_array_order():
    root = {"deck": _lua("table", 10)}

    assert physical_draw_pile_live_ids_from_live_memory(
        _Decoder(),
        root,
    ) == (8, 3, 11)


def test_env_r5_private_draw_order_rejects_sparse_array_before_replay():
    root = {"deck": _lua("table", 10)}

    with pytest.raises(LivePrivateRunStateError, match="not contiguous"):
        physical_draw_pile_live_ids_from_live_memory(
            _Decoder(indices=(1, 3, 4)),
            root,
        )


@pytest.mark.parametrize("live_ids", [(8, 8, 11), (8, 3.5, 11)])
def test_env_r5_private_draw_order_rejects_inexact_or_duplicate_ids(live_ids):
    root = {"deck": _lua("table", 10)}

    with pytest.raises(LivePrivateRunStateError, match="live ID|not unique"):
        physical_draw_pile_live_ids_from_live_memory(
            _Decoder(live_ids=live_ids),
            root,
        )
