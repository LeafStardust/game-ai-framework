import base64
import json
from pathlib import Path
import pytest
from games.mahjong_soul.live.runtime.visual import TileVision


def fixture():
    return json.loads((Path(__file__).parent/"fixtures/visual_red_sou.json").read_text(encoding="utf-8"))


def test_recorded_failed_hand_recognizes_all_tiles_and_exact_red_fives(monkeypatch):
    f=fixture();samples=iter(base64.b64decode(s) for s in f["samples"])
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.decode_frame",lambda _:b"pixels")
    # Tile-only samples do not contain the modal-heading region.
    monkeypatch.setattr(TileVision,"require_gameplay",lambda *args,**kwargs:None)
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.sample",lambda *args:next(samples))
    tiles,_=TileVision().hand(b"held-out frame",f["profile"],f["expected_hand"])
    assert tiles==f["visible_tiles"]
    assert tiles[0:2]==["0m","5m"] and tiles[6]=="0s"


def test_red_sou_must_not_silently_become_ordinary_five(monkeypatch):
    f=fixture();samples=iter(base64.b64decode(s) for s in f["samples"])
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.decode_frame",lambda _:b"pixels")
    # Tile-only samples do not contain the modal-heading region.
    monkeypatch.setattr(TileVision,"require_gameplay",lambda *args,**kwargs:None)
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.sample",lambda *args:next(samples))
    expected=["5s" if tile=="0s" else tile for tile in f["expected_hand"]]
    with pytest.raises(ValueError,match="differs from reader"):
        TileVision().hand(b"held-out frame",f["profile"],expected)
