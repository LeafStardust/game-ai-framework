from dataclasses import dataclass

from games.balatro.live.external.live_memory_hand_executor import (
    LiveMemoryHandExecutionError,
    resolve_live_hand_controls,
)


@dataclass(frozen=True)
class _Value:
    kind: str
    value: object


class _Decoder:
    def __init__(self, tables, arrays):
        self.tables = tables
        self.arrays = arrays

    def string_fields(self, address):
        return self.tables[int(address)]

    def array_items(self, address):
        return list(enumerate(self.arrays.get(int(address), [])))


def _num(value):
    return _Value("number", float(value))


def _text(value):
    return _Value("string", value)


def _table(address):
    return _Value("table", address)


def _fixture(*, include_discard=True):
    tables = {
        1: {"UIRoot": _table(2)},
        2: {"children": _table(3)},
        4: {"T": _table(40), "config": _table(41)},
        5: {"T": _table(50), "config": _table(51)},
        6: {"T": _table(60), "config": _table(61)},
        40: {"x": _num(7.2), "y": _num(10.05), "w": _num(2.5), "h": _num(1.4)},
        41: {"id": _text("play_button"), "func": _text("can_play")},
        50: {"x": _num(9.85), "y": _num(10.05), "w": _num(2.3), "h": _num(1.4)},
        51: {"id": _text("sort_button"), "func": _text("sort_hand")},
        60: {"x": _num(12.3), "y": _num(10.05), "w": _num(2.5), "h": _num(1.4)},
        61: {"id": _text("discard_button"), "func": _text("can_discard")},
    }
    children = [_table(4), _table(5)]
    if include_discard:
        children.append(_table(6))
    return _Decoder(tables, {3: children}), {"buttons": _table(1)}


def test_resolves_exact_live_play_and_discard_controls():
    decoder, root = _fixture()

    controls = resolve_live_hand_controls(decoder, root)

    assert controls.play.ui_id == "play_button"
    assert controls.play.callback == "can_play"
    assert controls.play.geometry["x"] == 7.2
    assert controls.discard.ui_id == "discard_button"
    assert controls.discard.callback == "can_discard"
    assert controls.discard.geometry["x"] == 12.3


def test_resolver_fails_closed_when_one_control_is_missing():
    decoder, root = _fixture(include_discard=False)

    try:
        resolve_live_hand_controls(decoder, root)
    except LiveMemoryHandExecutionError as error:
        assert "discard" in str(error)
    else:
        raise AssertionError("missing discard control must fail closed")
