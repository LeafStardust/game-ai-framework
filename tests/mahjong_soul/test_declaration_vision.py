"""Real button crops from the failed Ron run and reviewed Riichi/Tsumo panels."""
import base64
import json
from pathlib import Path
import zlib
import pytest
from games.mahjong_soul.live.runtime.visual import TileVision


@pytest.mark.parametrize("kind",["riichi","ron","tsumo"])
def test_recorded_declaration_labels_are_distinct_and_bind_to_actual_position(monkeypatch,kind):
    fixture=json.loads((Path(__file__).parent/"fixtures/visual_declarations.json").read_text(encoding="utf-8"))
    crop=zlib.decompress(base64.b64decode(fixture[kind]))
    rgb=bytearray(1920*1080*3)
    for row in range(110):rgb[((780+row)*1920+910)*3:((780+row)*1920+1130)*3]=crop[row*660:(row+1)*660]
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.decode_frame",lambda _:rgb)
    vision=TileVision()
    assert vision.button(b"recorded",kind)[:2]==(1020,835)
    for other in set(fixture)-{kind}:
        with pytest.raises(ValueError,match="not uniquely visible"):vision.button(b"recorded",other)
