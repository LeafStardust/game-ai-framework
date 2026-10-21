"""Counterfactual changes one legal call without remembering a phantom Pon."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from agents.mahjong_soul import call_counterfactual as cf


def setup_run(monkeypatch,*,repeat=False,missing_skip=False,different_deal=False):
    request=json.loads((Path(__file__).parent/'fixtures/south_pon_counterfactual.json').read_text())['request']
    original=deepcopy(request);calls=[]
    def fake_run(seed,seat,candidate,*,agent_factory,**kwargs):
        branch=len(calls);agent=agent_factory(candidate);agent.history=[{'type':'start_kyoku'}]
        req=deepcopy(request)
        if branch and missing_skip:req['actions']=[a for a in req['actions'] if a['kind']!='skip']
        action=agent.policy.choose(req)
        if repeat:agent.policy.choose(req)
        calls.append({'action':action,'plan':agent.policy._hand_plan})
        event={'type':'pon','actor':seat} if action['kind']=='pon' else {'type':'tsumo','actor':0,'pai':'1p'}
        return {'seed':seed,'seat':seat,'candidate':candidate,'scores':[35000]*3,'ranks':[1,2,3],
                'hands':1,'wins':0,'deal_ins':0,'initial_deal_digest':'other' if branch and different_deal else 'same',
                'log':[{'type':'start_kyoku'},event,{'type':'end_kyoku'},{'type':'end_game'}]}
    monkeypatch.setattr(cf,'run',fake_run)
    return request,original,calls


def test_exactly_one_legal_skip_does_not_remember_the_rejected_call(monkeypatch):
    request,before,calls=setup_run(monkeypatch)
    report,pon,skip=cf.compare_call(80,2,'2z')
    assert calls[0]['action']['kind']=='pon' and calls[0]['plan'] is not None
    assert calls[1]['action']=={'kind':'skip'} and calls[1]['plan'] is None
    assert report['overrides']==1 and report['first_different_event_index']==1
    assert pon[:1]==skip[:1] and request==before


@pytest.mark.parametrize('case,match',[('missing','not encountered'),('repeat','target repeated'),
                                      ('no_skip','legal Skip missing'),('deal','Starting deals differ')])
def test_unreached_or_invalid_counterfactual_is_rejected(monkeypatch,case,match):
    setup_run(monkeypatch,repeat=case=='repeat',missing_skip=case=='no_skip',different_deal=case=='deal')
    with pytest.raises(ValueError,match=match):
        cf.compare_call(80,2,'7z' if case=='missing' else '2z')


def test_occurrence_must_be_positive():
    with pytest.raises(ValueError,match='positive'):cf.compare_call(80,2,'2z',occurrence=0)
