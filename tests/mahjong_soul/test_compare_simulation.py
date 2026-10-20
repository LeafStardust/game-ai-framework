import pytest
from agents.mahjong_soul.compare_simulation import compare


def data():
    records=[]
    for seed in (0,1):
        for name,rank,wins in (("east_speed",2,0),("east_speed_push",1,1)):
            records.append({"seed":seed,"seat":0,"candidate":name,"ranks":[rank,2,3],"hands":2,"wins":wins,"deal_ins":0,"shape_tenpai_discards":[5],"initial_deal_digest":str(seed)})
    return {"records":records}


def test_paired_seed_metrics():
    result=compare(data())
    assert result["independent_seeds"]==2
    assert result["candidate_metrics"]["hand_win_rate"]==.5
    assert result["seed_cluster_bootstrap_95"]["average_rank"]==[-1,-1]


def test_missing_duplicate_or_different_deals_rejected():
    d=data();d["records"].pop()
    with pytest.raises(ValueError):compare(d)
    d=data();d["records"].append(d["records"][0])
    with pytest.raises(ValueError):compare(d)
    d=data();d["records"][0]["initial_deal_digest"]="wrong"
    with pytest.raises(ValueError):compare(d)


def test_identical_replays_do_not_count_as_candidate_exposure(tmp_path):
    import json
    from agents.mahjong_soul.compare_simulation import replay_coverage
    d=data();summary=tmp_path/"summary.json";summary.write_text(json.dumps(d))
    for r in d["records"]:
        (tmp_path/f"{r['seed']}-{r['seat']}-{r['candidate']}.json").write_text(json.dumps({"events":[{"type":"end_game"}]}))
    assert not replay_coverage(summary,"east_speed","east_speed_push")["candidate_exercised"]
    (tmp_path/"0-0-east_speed_push.json").write_text(json.dumps({"events":[{"type":"different"}]}))
    assert replay_coverage(summary,"east_speed","east_speed_push")["different_replays"]==1
