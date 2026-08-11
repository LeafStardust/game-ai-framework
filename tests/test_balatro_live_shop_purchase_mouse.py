from types import SimpleNamespace

import pytest

from games.balatro.live.external.live_shop_purchase_mouse import (
    LiveShopPurchaseMouseError,
    resolve_live_buy_target,
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


def _fixture(button="buy_from_shop", func="can_buy"):
    tables = {
        1: {"cursor_hover": _value("table", 2)},
        2: {"prev_target": _value("table", 3)},
        3: {"children": _value("table", 4)},
        4: {"buy_button": _value("table", 5)},
        5: {
            "UIRoot": _value("table", 6),
            "T": _value("table", 8),
            "VT": _value("table", 9),
        },
        6: {
            "config": _value("table", 7),
            "T": _value("table", 8),
            "VT": _value("table", 9),
        },
        7: {
            "button": _value("string", button),
            "func": _value("string", func),
        },
        8: {
            "x": _value("number", 10.920646),
            "y": _value("number", 6.671951),
            "w": _value("number", 1.1),
            "h": _value("number", 0.94),
            "r": _value("number", 0.0),
            "scale": _value("number", 1.0),
        },
        9: {
            "x": _value("number", 10.920646),
            "y": _value("number", 6.671951),
            "w": _value("number", 1.1),
            "h": _value("number", 0.94),
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


def test_live_buy_target_matches_validated_neptune_geometry():
    decoder, root = _fixture()

    target = resolve_live_buy_target(
        decoder,
        root,
        WindowRect(-1736, 165, 1536, 864),
    )

    assert target.container_address == 5
    assert target.ui_root_address == 6
    assert target.button == "buy_from_shop"
    assert target.func == "can_buy"
    assert target.geometry_source == "UIRoot VT"
    assert target.screen_center == PixelPoint(-858, 702)


def test_live_buy_target_rejects_buy_and_use_control():
    decoder, root = _fixture(func="can_buy_and_use")

    with pytest.raises(LiveShopPurchaseMouseError, match="not the ordinary Buy control"):
        resolve_live_buy_target(
            decoder,
            root,
            WindowRect(0, 0, 1536, 864),
        )
