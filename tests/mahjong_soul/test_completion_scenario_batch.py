"""Fail-closed, reusable public-request scenario evaluation."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from agents.mahjong_soul import completion_scenario_batch as batch
from agents.mahjong_soul.attack_value import own_player
from agents.mahjong_soul.policy import make_policy


def case():
    item = json.loads((Path(__file__).parent/'fixtures/call_width.json').read_text())[0]
    request = item['request'];policy = make_policy('playbook','atk');action = policy.choose(request)
    return {'profile':'callers','seed':80,'seat':1,'hand_index':1,'request':request,'action':action,
            'post_call_discard':policy.last_analysis['post_call_discard']['tile'],'baseline_exact_replay':True}


def test_branch_boards_preserve_request_and_record_the_post_call_discard():
    item = case(); original = deepcopy(item)
    before,after = batch.branch_boards(item)
    assert item == original
    assert before['visible_tile_counts'] == after['visible_tile_counts']
    assert len(after['self']['hand']) == len(before['self']['hand'])-3
    assert own_player(after)['discards'][-1]['tile'] == item['post_call_discard']
    assert len(own_player(after)['melds']) == len(own_player(before)['melds'])+1


def test_nonlegal_captured_call_rejected():
    item = case();item['action']['called_tile']='9z'
    with pytest.raises(ValueError,match='legal Pon'):batch.branch_boards(item)


def test_existing_report_preserved(tmp_path):
    output = tmp_path/'report.json';output.write_text('keep')
    with pytest.raises(ValueError,match='already exists'):
        batch.evaluate_requests(tmp_path/'missing.json',output)
    assert output.read_text()=='keep'


@pytest.mark.parametrize('complete,duplicate,verified',[(False,False,True),(True,True,True),(True,False,False)])
def test_incomplete_duplicate_or_unverified_source_rejected(tmp_path,complete,duplicate,verified):
    item = case();item['baseline_exact_replay']=verified
    rows = [item,item] if duplicate else [item]
    source=tmp_path/'source.json';source.write_text(json.dumps({'complete':complete,'records':rows,'eligible_calls':len(rows)}))
    output=tmp_path/'output.json'
    with pytest.raises(ValueError):batch.evaluate_requests(source,output)
    assert not output.exists()


def test_all_scenarios_keep_unavailable_estimates_explicit(tmp_path,monkeypatch):
    item = case();source=tmp_path/'source.json'
    source.write_text(json.dumps({'complete':True,'records':[item],'eligible_calls':1}))
    monkeypatch.setattr(batch,'estimate_completion',lambda *a,**kw:{'available':False,'reason':'state_budget'})
    output=tmp_path/'output.json';report=batch.evaluate_requests(source,output)
    assert report['complete'] is True
    assert len(report['records'][0]['scenarios'])==4
    assert all(v['preference']=='unavailable' for v in report['records'][0]['scenarios'].values())
    assert report['live_policy_changed'] is False


def test_failure_leaves_explicit_incomplete_report(tmp_path,monkeypatch):
    source=tmp_path/'source.json';source.write_text(json.dumps({'complete':True,'records':[case()],'eligible_calls':1}))
    def fail(*a,**kw):raise RuntimeError('interrupted')
    monkeypatch.setattr(batch,'estimate_completion',fail)
    output=tmp_path/'output.json'
    with pytest.raises(RuntimeError):batch.evaluate_requests(source,output)
    assert json.loads(output.read_text())['complete'] is False
