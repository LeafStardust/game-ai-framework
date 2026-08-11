from types import SimpleNamespace

import pytest

from games.balatro.live.external.live_shop_purchase_mouse import (
    LiveShopItemTarget,
    LiveShopPurchaseMouseError,
    _template_point,
    live_buy_hit_test,
    resolve_live_buy_and_use_target,
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


def _fixture(
    button="buy_from_shop",
    func="can_buy",
    *,
    hovered=False,
    child_name="buy_button",
):
    tables = {
        1: {"cursor_hover": _value("table", 2)},
        2: {"prev_target": _value("table", 3)},
        3: {"children": _value("table", 4)},
        4: {child_name: _value("table", 5)},
        5: {
            "UIRoot": _value("table", 6),
            "T": _value("table", 8),
            "VT": _value("table", 9),
        },
        6: {
            "config": _value("table", 7),
            "T": _value("table", 8),
            "VT": _value("table", 9),
            "states": _value("table", 10),
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
        10: {"hover": _value("table", 11)},
        11: {"is": _value("boolean", hovered)},
    }
    root = {
        "CONTROLLER": _value("table", 1),
        "TILE_W": _value("number", 20.0),
        "TILE_H": _value("number", 11.5),
    }
    return Decoder(tables), root


def test_live_buy_target_resolves_nested_neptune_geometry_guess():
    decoder, root = _fixture()

    target = resolve_live_buy_target(
        decoder,
        root,
        WindowRect(-1736, 165, 1536, 864),
    )

    assert target.action == "buy"
    assert target.container_address == 5
    assert target.ui_root_address == 6
    assert target.button == "buy_from_shop"
    assert target.func == "can_buy"
    assert target.geometry_source == "UIRoot VT"
    assert target.screen_center == PixelPoint(-858, 702)


def test_live_buy_and_use_target_requires_exact_control():
    decoder, root = _fixture(
        func="can_buy_and_use",
        child_name="buy_and_use_button",
    )

    target = resolve_live_buy_and_use_target(
        decoder,
        root,
        WindowRect(-1736, 165, 1536, 864),
    )

    assert target.action == "buy_and_use"
    assert target.child_name == "buy_and_use_button"
    assert target.button == "buy_from_shop"
    assert target.func == "can_buy_and_use"


def test_live_buy_hit_test_accepts_active_uiroot_hover():
    decoder, root = _fixture(hovered=True)
    target = resolve_live_buy_target(
        decoder,
        root,
        WindowRect(-1736, 165, 1536, 864),
    )

    hit, signal = live_buy_hit_test(decoder, root, target)

    assert hit is True
    assert signal == "states.hover.is:UIRoot"


def test_live_buy_hit_test_rejects_unverified_point():
    decoder, root = _fixture(hovered=False)
    target = resolve_live_buy_target(
        decoder,
        root,
        WindowRect(-1736, 165, 1536, 864),
    )

    hit, signal = live_buy_hit_test(decoder, root, target)

    assert hit is False
    assert signal == ""


def test_live_buy_target_rejects_buy_and_use_control():
    decoder, root = _fixture(func="can_buy_and_use")

    with pytest.raises(LiveShopPurchaseMouseError, match="not buy"):
        resolve_live_buy_target(
            decoder,
            root,
            WindowRect(0, 0, 1536, 864),
        )


def _item() -> LiveShopItemTarget:
    return LiveShopItemTarget(
        area="main",
        index=0,
        label="Neptune",
        live_id=321.0,
        ability_set="Planet",
        cost=3.0,
        geometry={
            "x": 10.446256,
            "y": 3.670488,
            "w": 2.048780,
            "h": 2.751220,
        },
        screen_center=PixelPoint(-858, 544),
    )


def test_buy_template_is_directly_below_shop_card():
    point = _template_point(
        _item(),
        action="buy",
        logical_width=20.0,
        logical_height=11.5,
        client_rect=WindowRect(-1736, 165, 1536, 864),
    )

    assert point.x == -858
    assert abs(point.y - 660) <= 1


def test_buy_and_use_template_is_right_of_shop_card():
    point = _template_point(
        _item(),
        action="buy_and_use",
        logical_width=20.0,
        logical_height=11.5,
        client_rect=WindowRect(-1736, 165, 1536, 864),
    )

    assert abs(point.x - (-761)) <= 1
    assert point.y == -1 + 545  # same mapped row as the item center, allowing fixture rounding
