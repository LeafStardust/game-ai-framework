from types import SimpleNamespace

import pytest

from games.balatro.live.external.live_shop_special_action_mouse import (
    LiveShopSpecialActionMouseError,
    _resolve_expected_from_node,
    _target_item,
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


def test_resolves_voucher_can_redeem_without_button():
    decoder = Decoder({
        1: {"config": _value("table", 2)},
        2: {"func": _value("string", "can_redeem")},
    })

    resolved = _resolve_expected_from_node(
        decoder,
        _value("table", 1),
        "cursor_hover.target",
        "vouchers",
    )

    assert resolved is not None
    address, button, func, control_id, signal = resolved
    assert address == 1
    assert button is None
    assert func == "can_redeem"
    assert control_id is None
    assert signal == "cursor_hover.target.parent[0]"


def test_resolves_booster_use_card_can_open():
    decoder = Decoder({
        1: {"config": _value("table", 2)},
        2: {
            "button": _value("string", "use_card"),
            "func": _value("string", "can_open"),
        },
    })

    resolved = _resolve_expected_from_node(
        decoder,
        _value("table", 1),
        "cursor_hover.target",
        "boosters",
    )

    assert resolved is not None
    assert resolved[1] == "use_card"
    assert resolved[2] == "can_open"


def test_booster_target_uses_live_geometry_and_cost():
    snapshot = SimpleNamespace(
        phase="SHOP",
        payload={
            "money": 7,
            "shop_boosters": {
                "cards": [{
                    "area_index": 0,
                    "label": "Jumbo Standard Pack",
                    "live_id": 10,
                    "cost": 6.0,
                    "ui": {"x": 12.0, "y": 8.0, "w": 2.0, "h": 2.0},
                }],
            },
        },
    )

    target = _target_item(
        snapshot,
        "boosters",
        0,
        logical_width=20.0,
        logical_height=11.5,
        client_rect=WindowRect(0, 0, 1536, 864),
    )

    assert target.label == "Jumbo Standard Pack"
    assert target.cost == 6.0
    assert isinstance(target.screen_center, PixelPoint)


def test_special_action_refuses_unaffordable_item():
    snapshot = SimpleNamespace(
        phase="SHOP",
        payload={
            "money": 7,
            "shop_vouchers": {
                "cards": [{
                    "area_index": 0,
                    "label": "Wasteful",
                    "cost": 10.0,
                    "ui": {"x": 6.0, "y": 8.0, "w": 2.0, "h": 2.0},
                }],
            },
        },
    )

    with pytest.raises(LiveShopSpecialActionMouseError, match="unaffordable"):
        _target_item(
            snapshot,
            "vouchers",
            0,
            logical_width=20.0,
            logical_height=11.5,
            client_rect=WindowRect(0, 0, 1536, 864),
        )
