import pytest
from games.mahjong_soul.live.runtime.visual import TileVision


def profile():
    return {"trigger":"ActionChiPengGang","slots":[[.14+i*.0495,.9268] for i in range(11)]}


def test_extra_standing_call_tile_rejects_shortened_hand_without_guessing_reader(monkeypatch):
    vision=TileVision();reference=next(value for tile,value in vision.tiles if tile=="5z")
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.sample",lambda *a:reference)
    with pytest.raises(ValueError,match="Call animation"):
        vision.require_settled_call(b"rgb",profile())


def test_unrecognized_empty_tail_and_regular_draw_are_not_rejected(monkeypatch):
    vision=TileVision();monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.sample",lambda *a:bytes(648))
    vision.require_settled_call(b"rgb",profile())
    p=profile();p["trigger"]="ActionDealTile"
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.sample",lambda *a:pytest.fail("Not a call"))
    vision.require_settled_call(b"rgb",p)
