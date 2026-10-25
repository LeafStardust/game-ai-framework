from random import Random
import pytest
from games.mahjong_soul.live.runtime.visual import TileVision,distance,_pack_sample,_packed_distance


def test_packed_distance_exact_for_extreme_alternating_and_random_channels():
    rng=Random(612)
    cases=[(bytes([a])*648,bytes([b])*648) for a in (0,1,127,128,254,255) for b in (0,1,127,128,254,255)]
    cases += [(bytes([0,255])*324,bytes([255,0])*324)]
    cases += [(rng.randbytes(648),rng.randbytes(648)) for _ in range(150)]
    for a,b in cases:
        assert _packed_distance(_pack_sample(a),_pack_sample(b))==distance(a,b)
    with pytest.raises(ValueError):_pack_sample(b"short")


def test_every_label_distance_preserves_original_bank_minimum_and_ambiguity():
    vision=TileVision();rng=Random(19)
    queries=[v for _,v in vision.tiles[::35]]+[rng.randbytes(648) for _ in range(3)]
    for value in queries:
        original={}
        for tile,reference in vision.tiles:
            original[tile]=min(original.get(tile,float("inf")),distance(value,reference))
        assert dict(vision._tile_scores(value))==original
    with pytest.raises(ValueError):vision.classify(bytes(648))


def test_cache_is_bounded_per_instance_and_returns_independent_diagnostics():
    first=TileVision();second=TileVision();value=first.tiles[0][1]
    expected=first.scores(value);expected[0]["tile"]="changed"
    assert first.scores(value)[0]["tile"]!="changed"
    assert first._tile_scores.cache_info().hits==1
    assert second._tile_scores.cache_info().currsize==0
    assert first._tile_scores.cache_info().maxsize==2048


def test_packed_shape_scores_preserve_every_label_exactly():
    vision=TileVision();rng=Random(823)
    for value in [v for _,v in vision.tiles[::35]]+[rng.randbytes(648)]:
        query=bytes(min(value[i:i+3]) for i in range(0,len(value),3))
        expected={}
        for tile,reference in vision._shape_tiles:
            error=sum(abs(a-b) for a,b in zip(query,reference))/len(query)
            expected[tile]=min(expected.get(tile,999),error)
        assert dict(vision._shape_scores(value))==expected
    assert vision._shape_scores.cache_info().maxsize==2048


def test_unfinished_draw_exits_before_sampling_standing_hand(monkeypatch):
    vision=TileVision();sampled=[]
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.decode_frame",lambda _:b"rgb")
    monkeypatch.setattr(vision,"require_gameplay",lambda *a,**k:None)
    def capture(rgb,x,y):
        sampled.append((x,y))
        return bytes(648)
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.sample",capture)
    monkeypatch.setattr(vision,"classify",lambda value:(_ for _ in ()).throw(ValueError("Unknown")))
    monkeypatch.setattr(vision,"align_tile",lambda *a:(_ for _ in ()).throw(ValueError("Unknown")))
    profile={"client_size":[1920,1080],"trigger":"ActionDealTile",
             "slots":[[.2,.9],[.3,.9],[.4,.9]]}
    with pytest.raises(ValueError,match="Slot 2"):
        vision.hand(b"frame",profile,["1p","2p","3p"])
    assert sampled==[(round(.4*1919),round(.9*1079))]
