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
