"""Keep completion-based call decisions isolated to an offline candidate."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from agents.mahjong_soul.policy import make_policy
from agents.mahjong_soul.completion_call_guard import guard_opening
from agents.mahjong_soul.attack_value import own_player


def request():return json.loads((Path(__file__).parent/'fixtures/call_width.json').read_text())[0]['request']


def policy():
    p=make_policy('playbook','atk')
    p.registry.get(3,'atk','east').strategy['calls']['completion_opening_guard']=True
    return p


def test_candidate_changes_the_diagnostic_opening_without_changing_live_defaults():
    req=request();original=deepcopy(req);normal=make_policy('playbook','atk');candidate=policy()
    assert normal.choose(req)['kind']=='pon'
    assert candidate.choose(req)=={'kind':'skip'}
    notes=candidate.last_analysis['call_evaluations']
    assert any(n.get('completion_guard',{}).get('rejected') for n in notes)
    assert not normal.registry.get(3,'atk','east').strategy['calls'].get('completion_opening_guard')
    assert not candidate.registry.get(4,'atk','east').strategy['calls'].get('completion_opening_guard')
    assert not candidate.registry.get(4,'atk','south').strategy['calls'].get('completion_opening_guard')
    assert req==original


def selected():
    req=request();normal=make_policy('playbook','atk');action=normal.choose(req)
    option={'shanten':1,'open_yaku':False,'action':normal.last_analysis['post_call_discard']}
    return req['observation']['board'],[(action,option)]


def test_unavailable_forecast_preserves_the_original_call():
    board,candidates=selected();calls=[]
    def unavailable(*a,**kw):calls.append(True);return {'available':False,'reason':'state_budget'}
    assert guard_opening(board,candidates,estimator=unavailable)==candidates[0]
    assert len(calls)==1


def test_secured_yaku_or_immediate_tenpai_never_invokes_the_estimator():
    def fail(*a,**kw):raise AssertionError('Protected call was evaluated')
    for key,value in [('open_yaku',True),('shanten',0)]:
        board,candidates=selected();candidates[0][1][key]=value
        assert guard_opening(board,candidates,estimator=fail)==candidates[0]


def test_already_open_hand_is_not_filtered():
    board,candidates=selected();own_player(board)['melds']=[{'type':1,'tiles':['1m']*3}]
    def fail(*a,**kw):raise AssertionError('Later call was evaluated')
    assert guard_opening(board,candidates,estimator=fail)==candidates[0]
