import pytest
from agents.mahjong_soul.pattern_yaku import pattern_targets,pattern_progress
from tests.mahjong_soul.test_attack_v2 import board
from tests.mahjong_soul.test_efficiency import tiles

CASES=[("pinfu","234m345p456678s22p","8s"),
       ("iipeikou","123123m456p789s55z","9s"),
       ("ryanpeikou","112233m445566p77s","6p"),
       ("sanshoku","123m123p123s789m55z","9m"),
       ("ittsu","123456789m234s55p","4s"),
       ("sanshoku_doukou","222m222p222s456s55z","6s"),
       ("sanankou","222m444p666888s55p","8s"),
       ("shousangen","55566677z123m789p","9p"),
       ("chanta","123m789p111z789s55z","9s"),
       ("junchan","123789m123789p11s","9p"),
       ("honroutou","111999m111p999s55z","9s")]


@pytest.mark.parametrize("name,full,win",CASES)
def test_each_new_structural_route_reaches_a_real_ready_shape(name,full,win):
    b=board(full);hand=b["self"]["hand"];hand.remove(win)
    targets=[t for t in pattern_targets(b,hand,0) if t["target_route"]==name]
    assert targets,name
    assert min(t["pattern_shanten"] for t in targets)==0
    candidates=[t for t in targets if t["pattern_shanten"]==0]
    assert any(win in {x["tile"] for x in pattern_progress(b,hand,t)[1]} for t in candidates)


def test_pinfu_does_not_stack_value_honor_triplets_and_ryanpeikou_consumes_all_four_melds():
    b=board("111z123m456p789s22p")
    for t in pattern_targets(b,b["self"]["hand"],0):
        if t["target_route"]=="pinfu":assert t["projected_han"]==2
    b=board("112233m445566p77s")
    for t in pattern_targets(b,b["self"]["hand"],0):
        if t["target_route"]=="ryanpeikou":assert t["projected_han"]==4


def test_open_meld_cannot_supply_a_concealed_triplet_or_closed_sequence_yaku():
    b=board("222p666s123m55z",melds=[{"type":1,"tiles":tiles("444s")}])
    targets=pattern_targets(b,b["self"]["hand"],0)
    assert not any(t["target_route"] in ("pinfu","iipeikou","ryanpeikou") for t in targets)
    # The existing open Pon cannot be reserved as one of three concealed sets.
    for t in targets:
        if t["target_route"]=="sanankou":assert t["concealed_required"] is True


def test_mandatory_sanankou_groups_do_not_keep_an_isolated_dora():
    b=board("66p3m99m999s66s1z",melds=[{"type":0,"tiles":tiles("234s")}],doras=["2m"])
    targets=[t for t in pattern_targets(b,b["self"]["hand"],1) if t["target_route"]=="sanankou" and t["pattern_shanten"]==1]
    assert targets
    assert all(t["projected_han"]==2 for t in targets)


def test_honroutou_supports_both_triplet_and_seven_pairs_forms():
    b=board("1199m1199p1199s1z")
    targets=[t for t in pattern_targets(b,b["self"]["hand"],0) if t["target_route"]=="honroutou_pairs"]
    assert targets and targets[0]["pattern_shanten"]==0 and targets[0]["projected_han"]==5
