from dataclasses import dataclass

from games.balatro.live.external.live_memory_hand_executor import (
    LiveMemoryHandExecutionError,
    LiveMemoryHandExecutor,
    resolve_live_hand_controls,
)
from games.balatro.live.external.window import BalatroWindow, WindowRect


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


class _Observer:
    def __init__(self, decoder, root):
        self.decoder = decoder
        self.root = root

    def _root(self):
        return self.decoder, 999, self.root


class _WindowLocator:
    def __init__(self, window):
        self.window = window

    def refresh(self, handle):
        assert handle == self.window.handle
        return self.window


class _Mouse:
    def __init__(self):
        self.points = []

    def click_screen(self, point, *, window=None):
        self.points.append(point)


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


def test_live_card_click_rereads_geometry_after_hand_reflow():
    decoder = _Decoder(
        {
            70: {"T": _table(71)},
            71: {
                "x": _num(4.0),
                "y": _num(7.0),
                "w": _num(2.0),
                "h": _num(2.5),
            },
        },
        {},
    )
    root = {"TILE_W": _num(20.0), "TILE_H": _num(11.5)}
    window = BalatroWindow(
        handle=123,
        title="Balatro",
        client_rect=WindowRect(left=100, top=200, width=1536, height=864),
    )
    mouse = _Mouse()
    executor = LiveMemoryHandExecutor(
        _Observer(decoder, root),
        mouse=mouse,
        window_locator=_WindowLocator(window),
    )

    executor._click_live_card(70, window, label="H0")
    first = mouse.points[-1]

    # Simulate Balatro re-fanning the same live card object after another card was
    # selected. A stale snapshot target would click the old point; production must
    # read T again from address 70.
    decoder.tables[71]["x"] = _num(8.0)
    decoder.tables[71]["y"] = _num(6.5)

    executor._click_live_card(70, window, label="H0")
    second = mouse.points[-1]

    assert second != first
    assert second.x > first.x
