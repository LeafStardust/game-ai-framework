from types import SimpleNamespace

import pytest

from games.balatro.live.external.live_shop_next_round_mouse import (
    LiveShopNextRoundMouseError,
    resolve_live_next_round_target,
)
from games.balatro.live.external.viewport import PixelPoint
from games.balatro.live.external.window import WindowRect


def _value(kind, value):
    return SimpleNamespace(kind=kind, value=value)


class Decoder:

    def __init__(self, tables):
        self.tables = tables

    def string_fields(self, address):
        return self.tables[int(address)]


def _fixture(button="toggle_shop", control_id="next_round_button"):
    tables = {
        1: {"snap_cursor_to": _value("table", 2)},
        2: {"node": _value("table", 3)},
        3: {
            "config": _value("table", 4),
            "T": _value("table", 5),
            "VT": _value("table", 6),
        },
        4: {
            "button": _value("string", button),
            "id": _value("string", control_id),
        },
        5: {
            "x": _value("number", 5.478659),
            "y": _value("number", 3.996341),
            "w": _value("number", 2.8),
            "h": _value("number", 1.5),
            "r": _value("number", 0.0),
            "scale": _value("number", 1.0),
        },
        6: {
            "x": _value("number", 5.478659),
            "y": _value("number", 3.996341),
            "w": _value("number", 2.8),
            "h": _value("number", 1.5),
            "r": _value("number", 0.0),
            "scale": _value("number", 1.0),
        },
    }
    root = {
        "CONTROLLER": _value("table", 1),
        "TILE_W": _value("number", 20.0),
        "TILE_H": _value("number", 11.5),
    }
    return Decoder(tables), root


def test_live_next_round_target_matches_validated_geometry():
    decoder, root = _fixture()

    target = resolve_live_next_round_target(
        decoder,
        root,
        WindowRect(-1736, 165, 1536, 864),
    )

    assert target.node_address == 3
    assert target.button == "toggle_shop"
    assert target.control_id == "next_round_button"
    assert target.geometry_source == "VT"
    assert target.screen_center == PixelPoint(-1203, 522)


def test_live_next_round_target_rejects_non_next_round_snap_node():
    decoder, root = _fixture(button="reroll_shop", control_id="reroll_shop")

    with pytest.raises(LiveShopNextRoundMouseError, match="not the Next Round control"):
        resolve_live_next_round_target(
            decoder,
            root,
            WindowRect(0, 0, 1536, 864),
        )
