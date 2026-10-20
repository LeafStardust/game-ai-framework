import json
from agents.mahjong_soul.benchmark import benchmark,rate


def recording(tmp_path,seat=1,restored=False):
    p=tmp_path/"session";p.mkdir();path=p/"events.jsonl"
    rows=[{"kind":"configuration","revision":"abc"},
          {"kind":"frame","report":{"game_connection":"g","state":{"seat":seat,"player_count":3,"status":"tracking","lobby":{"match_length":"east"}}}},
          {"kind":"game_event","connection":"g","event":{"name":"ActionNewRound","source":"restore" if restored else "live","step":0,"data":{"chang":0,"ju":0,"ben":0}}},
          {"kind":"game_event","connection":"g","event":{"name":"ActionDiscardTile","source":"live","step":1,"data":{"seat":0}}},
          {"kind":"game_event","connection":"g","event":{"name":"ActionHule","source":"live","step":2,"data":{"hules":[{"seat":1,"zimo":False},{"seat":2,"zimo":False}]}}},
          {"kind":"blocked"},
          {"kind":"frame","report":{"game_connection":"g","state":{"seat":seat,"player_count":3,"status":"match_ended","scores":[10000,50000,45000]}}}]
    path.write_text("\n".join(json.dumps(r) for r in rows));return path,rows


def test_auto_win_outcomes_deduplication_and_halts_are_counted(tmp_path):
    path,rows=recording(tmp_path,restored=True)
    result=benchmark([path,path]);m=result["matches"][0]
    assert m["complete"] and m["hand_wins"]==1 and m["hands"]==1 and m["rank_by_score"]==1
    assert m["deal_ins"]==0 and result["groups"][0]["matches"]==1
    assert m["issues"]["blocked"]>=1


def test_double_ron_is_one_deal_in_hand_and_partial_matches_excluded(tmp_path):
    path,rows=recording(tmp_path,seat=0)
    assert benchmark([path])["matches"][0]["deal_ins"]==1
    path.write_text("\n".join(json.dumps(r) for r in rows[:-1]))
    result=benchmark([path]);assert not result["matches"][0]["complete"] and not result["groups"]


def test_uncertainty_and_score_ties(tmp_path):
    assert rate(0,0)["rate"] is None
    assert rate(0,1)["wilson_95"][1]>.7
    path,rows=recording(tmp_path);rows[-1]["report"]["state"]["scores"]=[10000,50000,50000]
    path.write_text("\n".join(json.dumps(r) for r in rows))
    group=benchmark([path])["groups"][0]
    assert group["first_place"]["total"]==0 and group["average_rank_untied"] is None
