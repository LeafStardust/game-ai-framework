"""Positive complete-hand conformance cases for every standard catalog entry."""
from copy import deepcopy
import pytest
from agents.mahjong_soul.scoring import score_hand,nagashi_eligible
from agents.mahjong_soul.yaku_catalog import catalog
from tests.mahjong_soul.test_efficiency import tiles

# Cases may stack Yaku; the canonical evaluator must choose a legal maximal
# decomposition and suppress incompatible lower Yaku itself.
CASES=[
 ("tsumo","123456m789p234s55p","4s",{"tsumo":True}),
 ("riichi","123456m789p234s55p","4s",{"riichi":True}),
 ("daburu_riichi","123456m789p234s55p","4s",{"riichi":True,"context":{"double_riichi":True}}),
 ("ippatsu","123456m789p234s55p","4s",{"riichi":True,"context":{"ippatsu":True}}),
 ("chankan","123456m789p234s55p","4s",{"context":{"chankan":True}}),
 ("rinshan","123456m789p234s55p","4s",{"tsumo":True,"context":{"rinshan":True}}),
 ("haitei","123456m789p234s55p","4s",{"tsumo":True,"context":{"haitei":True}}),
 ("houtei","123456m789p234s55p","4s",{"context":{"houtei":True}}),
 ("nagashi_mangan","123456m789p234s55p","4s",{"tsumo":True,"context":{"nagashi_mangan":True}}),
 ("pinfu","234m345p456678s22p","8s",{}),
 ("tanyao","234m345p456678s22p","8s",{}),
 ("iipeiko","123123m456p789s55z","9s",{}),
 ("sanshoku","123m123p123s789m55z","9m",{}),
 ("ittsu","123456789m234s55p","4s",{}),
 ("chantai","123m789p111z789s55z","9s",{}),
 ("honroto","111999m111p999s55z","9s",{}),
 ("toitoi","222m444p666888s55p","8s",{}),
 ("sanankou","222m444p666888s55p","8s",{}),
 ("sanshoku_douko","222m222p222s456s55z","6s",{}),
 ("chiitoitsu","1122m3344p5566s77z","7z",{}),
 ("shosangen","55566677z123m789p","9p",{}),
 ("honitsu","123456789m111z22m","9m",{}),
 ("junchan","123789m123789p11s","9p",{}),
 ("ryanpeiko","112233m445566p77s","6p",{}),
 ("chinitsu","123123456789m55m","9m",{}),
 ("kokushi","119m19p19s1234567z","9m",{}),
 ("daburu_kokushi","119m19p19s1234567z","1m",{}),
 ("chuuren_poutou","11123455678999m","1m",{}),
 ("daburu_chuuren_poutou","11123455678999m","5m",{}),
 ("suuankou","222m444p666888s55z","8s",{"tsumo":True}),
 ("suuankou_tanki","222m444p666888s55z","5z",{}),
 ("daisangen","555666777z123m22p","3m",{}),
 ("shosuushi","11122233344z123m","3m",{}),
 ("daisuushi","111222333444z55m","4z",{}),
 ("ryuisou","222333444666s66z","6s",{"tsumo":True}),
 ("tsuisou","11122233355566z","5z",{"tsumo":True}),
 ("chinroto","111999m111999p11s","9p",{"tsumo":True}),
 ("tenhou","123456m789p234s55p","4s",{"tsumo":True,"context":{"tenhou":True}}),
 ("chiihou","123456m789p234s55p","4s",{"tsumo":True,"seat_wind":1,"context":{"chiihou":True}}),
 ("dora","123456m789p234s55p","4s",{"riichi":True,"doras":["4p"]}),
 ("aka_dora","123456m789p234s05p","4s",{"riichi":True}),
 ("ura_dora","123456m789p234s55p","4s",{"riichi":True,"ura":["4p"]}),
]
for key,tile in (("haku","5z"),("hatsu","6z"),("chun","7z")):
    CASES.append((key,"123m456p789s55p"+tile[0]*3+"z","9s",{}))
for wind in range(4):
    honor=str(wind+1)+"z";full="123m456p789s55p"+str(wind+1)*3+"z"
    name=("east","south","west","north")[wind]
    CASES.append(("seat_wind_"+name,full,"9s",{"seat_wind":wind,"round_wind":(wind+1)%4}))
    CASES.append(("round_wind_"+name,full,"9s",{"seat_wind":(wind+1)%4,"round_wind":wind}))
QUADS=[{"type":2,"tiles":tiles(g)} for g in ("1111m","2222p","3333s")]
CASES.append(("sankantsu","444p55z","4p",{"melds":QUADS}))
CASES.append(("suukantsu","55z","5z",{"melds":QUADS+[{"type":2,"tiles":tiles("4444p")}]}))


def evaluate(full,win,kwargs):
    hand=tiles(full);hand.remove(win)
    return score_hand(hand,win,**kwargs)


@pytest.mark.parametrize("key,full,win,kwargs",CASES,ids=[c[0] for c in CASES])
def test_every_standard_yaku_has_a_scoring_example(key,full,win,kwargs):
    result=evaluate(full,win,kwargs)
    assert result["legal"],result
    assert key in {y["key"] for y in result["yaku_details"]},result
    assert result["han"]>0 and result["points"]>0


def test_catalog_coverage_is_complete_and_dora_is_not_a_yaku():
    assert {c[0] for c in CASES}=={y["key"] for y in catalog()}
    assert {y["key"] for y in catalog() if y["bonus"]}=={"dora","aka_dora","ura_dora"}
    full="123456m789p234s55p";fixed=[{"type":0,"tiles":tiles("123m")}]
    result=evaluate("456m789p234s55p","4s",{"melds":fixed,"doras":["4p"]})
    assert not result["legal"]


def test_closed_only_patterns_are_lost_on_opening_and_dora_does_not_restore_them():
    result=evaluate("123m456p789s55z","9s",{"melds":[{"type":0,"tiles":tiles("123m")}],"doras":["4z"]})
    assert not result["legal"]
    result=evaluate("123m456p789s55z","9s",{"melds":[{"type":0,"tiles":tiles("123m")}],"riichi":True})
    assert not result["legal"]


def test_double_yakuman_and_stacking_are_explained_in_result():
    result=evaluate("111222333444z55m","5m",{})
    keys={y["key"] for y in result["yaku_details"]}
    assert {"daisuushi","suuankou_tanki"}<=keys
    assert result["yakuman_multiplier"]==4 and result["han"]==52


def test_illegal_tile_copies_and_malformed_melds_are_rejected():
    assert not evaluate("11111m234p567s999z","1m",{})["legal"]
    assert not evaluate("123m456p789s55z","9s",{"melds":[{"type":0,"tiles":tiles("124m")} ]})["legal"]


def test_ura_requires_riichi_and_ippatsu_requires_riichi():
    with_ura=evaluate("123456m789p234s55p","4s",{"tsumo":True,"ura":["4p"]})
    assert "ura_dora" not in {y["key"] for y in with_ura["yaku_details"]}
    assert not evaluate("123456m789p234s55p","4s",{"context":{"ippatsu":True}})["legal"]


@pytest.mark.parametrize("key,full,win,group,closed_han,open_han",[
 ("ittsu","123456789m234s55p","4s","123m",2,1),
 ("sanshoku","123m123p123s789m55z","9m","123m",2,1),
 ("chantai","123m789p111z789s55z","9s","123m",2,1),
 ("junchan","123789m123789p11s","9p","123m",3,2),
 ("honitsu","123456789m111z22m","9m","123m",3,2),
 ("chinitsu","123123456789m55m","9m","123m",6,5),
 ("toitoi","222m444p666888s55p","8s","222m",2,2),
])
def test_open_closed_han_values_are_enforced_by_scoring(key,full,win,group,closed_han,open_han):
    closed=evaluate(full,win,{})
    hand=tiles(full)
    for t in tiles(group):hand.remove(t)
    hand.remove(win)
    opened=score_hand(hand,win,melds=[{"type":0 if len(set(tiles(group)))==3 else 1,"tiles":tiles(group)}])
    assert closed["legal"] and opened["legal"]
    assert next(y["han"] for y in closed["yaku_details"] if y["key"]==key)==closed_han
    assert next(y["han"] for y in opened["yaku_details"] if y["key"]==key)==open_han


def test_points_fu_limit_and_actual_yakuman_are_distinct_from_counted_yakuman():
    normal=evaluate("123456m789p234s55p","4s",{"seat_wind":1})
    assert (normal["han"],normal["fu"],normal["points"],normal["limit"])==(1,30,1000,"ordinary")
    dealer=evaluate("123456m789p234s55p","4s",{})
    assert dealer["points"]==1500
    counted=evaluate("123123456789m55m","9m",{"riichi":True,"doras":["4m","4m"],"seat_wind":1})
    assert counted["limit"]=="counted_yakuman" and counted["points"]==32000
    assert counted["yakuman_multiplier"]==0
    stacked=evaluate("111222333444z55m","5m",{"seat_wind":1})
    assert stacked["points"]==128000 and stacked["yakuman_multiplier"]==4


def test_honba_and_riichi_sticks_are_not_disguised_as_hand_han():
    r=evaluate("123456m789p234s55p","4s",{"seat_wind":1,"honba":2,"riichi_sticks":3})
    assert r["han"]==1 and r["points"]==1000
    assert r["points_with_honba"]==1600 and r["riichi_sticks"]==3000


def test_chankan_can_stack_with_ippatsu_but_not_houtei_or_tsumo():
    r=evaluate("123456m789p234s55p","4s",{"riichi":True,"context":{"ippatsu":True,"chankan":True}})
    assert {"riichi","ippatsu","chankan"}<={y["key"] for y in r["yaku_details"]}
    assert not evaluate("123456m789p234s55p","4s",{"tsumo":True,"context":{"chankan":True}})["legal"]
    assert not evaluate("123456m789p234s55p","4s",{"context":{"chankan":True,"houtei":True}})["legal"]
