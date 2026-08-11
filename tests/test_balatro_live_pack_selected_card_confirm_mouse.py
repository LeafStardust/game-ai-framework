from types import SimpleNamespace

from games.balatro.live.external.live_pack_selected_card_confirm_mouse import (
    _memory_confirm_candidates,
    _resolve_confirm,
)


def _value(kind, value):
    return SimpleNamespace(kind=kind, value=value)


class Decoder:
    def __init__(self, tables):
        self.tables = tables

    def string_fields(self, address):
        return self.tables[int(address)]

    def array_items(self, address):
        return []


class Observer:
    def __init__(self, decoder, root):
        self.decoder = decoder
        self.root = root

    def _root(self):
        return self.decoder, 0, self.root


def test_resolve_confirm_requires_exact_identity():
    decoder = Decoder(
        {
            1: {"config": _value("table", 2)},
            2: {
                "button": _value("string", "use_card"),
                "func": _value("string", "can_select_card"),
            },
            3: {"config": _value("table", 4)},
            4: {
                "button": _value("string", "use_card"),
                "func": _value("string", "can_open"),
            },
        }
    )

    resolved = _resolve_confirm(
        decoder,
        _value("table", 1),
        "cursor_hover.target",
    )
    assert resolved is not None
    address, button, func, control_id, signal = resolved
    assert address == 1
    assert button == "use_card"
    assert func == "can_select_card"
    assert control_id is None
    assert signal == "cursor_hover.target.parent[0]"

    assert (
        _resolve_confirm(
            decoder,
            _value("table", 3),
            "cursor_hover.target",
        )
        is None
    )


def test_memory_confirm_candidates_find_exact_live_ui_geometry():
    decoder = Decoder(
        {
            10: {"confirm": _value("table", 11)},
            11: {
                "config": _value("table", 12),
                "T": _value("table", 13),
                "VT": _value("table", 14),
            },
            12: {
                "button": _value("string", "use_card"),
                "func": _value("string", "can_select_card"),
            },
            13: {
                "x": _value("number", 1.0),
                "y": _value("number", 2.0),
                "w": _value("number", 3.0),
                "h": _value("number", 4.0),
            },
            14: {
                "x": _value("number", 5.0),
                "y": _value("number", 6.0),
                "w": _value("number", 1.0),
                "h": _value("number", 0.5),
            },
        }
    )
    root = {
        "TILE_W": _value("number", 20.0),
        "TILE_H": _value("number", 11.5),
        "UIDEF": _value("table", 10),
    }

    candidates, tile_w, tile_h = _memory_confirm_candidates(
        Observer(decoder, root)
    )

    assert tile_w == 20.0
    assert tile_h == 11.5
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.node_address == 11
    assert candidate.geometry_source == "VT"
    assert candidate.geometry["x"] == 5.0
    assert candidate.geometry["y"] == 6.0
    assert candidate.geometry["w"] == 1.0
    assert candidate.geometry["h"] == 0.5
