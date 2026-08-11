from types import SimpleNamespace

from games.balatro.live.external.live_shop_reroll_mouse import (
    _resolve_reroll_from_node,
)


def _value(kind, value):
    return SimpleNamespace(kind=kind, value=value)


class Decoder:
    def __init__(self, tables):
        self.tables = tables

    def string_fields(self, address):
        return self.tables[int(address)]


def test_resolve_reroll_from_current_hover_node():
    decoder = Decoder(
        {
            1: {
                "config": _value("table", 2),
            },
            2: {
                "button": _value("string", "reroll_shop"),
                "func": _value("string", "can_reroll"),
            },
        }
    )

    resolved = _resolve_reroll_from_node(
        decoder,
        _value("table", 1),
        "cursor_hover.target",
    )

    assert resolved is not None
    address, button, func, control_id, signal = resolved
    assert address == 1
    assert button == "reroll_shop"
    assert func == "can_reroll"
    assert control_id is None
    assert signal == "cursor_hover.target.parent[0]"


def test_resolve_reroll_rejects_other_shop_control():
    decoder = Decoder(
        {
            1: {
                "config": _value("table", 2),
            },
            2: {
                "button": _value("string", "toggle_shop"),
                "func": _value("string", "can_shop"),
            },
        }
    )

    assert (
        _resolve_reroll_from_node(
            decoder,
            _value("table", 1),
            "cursor_hover.target",
        )
        is None
    )
