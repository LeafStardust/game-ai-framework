from types import SimpleNamespace

import pytest

from games.balatro.live.external.live_round_eval_mouse import (
    LiveRoundEvalMouseError,
    resolve_live_cash_out_target,
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


def _fixture(button="cash_out", control_id="cash_out_button"):
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
            "x": _value("number", 7.508659),
            "y": _value("number", 4.1),
            "w": _value("number", 7.0),
            "h": _value("number", 1.0964),
            "r": _value("number", 0.0),
            "scale": _value("number", 1.0),
        },
        6: {
            "x": _value("number", 7.508659),
            "y": _value("number", 4.1),
            "w": _value("number", 7.0),
            "h": _value("number", 1.0964),
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


def test_live_cash_out_target_matches_validated_geometry():
    decoder, root = _fixture()

    target = resolve_live_cash_out_target(
        decoder,
        root,
        WindowRect(-1736, 165, 1536, 864),
    )

    assert target.node_address == 3
    assert target.button == "cash_out"
    assert target.control_id == "cash_out_button"
    assert target.geometry_source == "VT"
    assert target.screen_center == PixelPoint(-892, 514)


def test_live_cash_out_target_rejects_non_cash_out_snap_node():
    decoder, root = _fixture(button="play", control_id="play_button")

    with pytest.raises(LiveRoundEvalMouseError, match="not the Cash Out control"):
        resolve_live_cash_out_target(
            decoder,
            root,
            WindowRect(0, 0, 1536, 864),
        )
