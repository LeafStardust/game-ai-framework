"""Do not mistake a narrow unsecured opening for faster winning progress."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from agents.mahjong_soul.policy import make_policy
from tests.mahjong_soul.test_scored_ready_yaku import safe_pair_wait
from tests.mahjong_soul.test_sanma_east_speed import sanma
from games.mahjong_soul.live.runtime.decision import decision_request


def cases():return json.loads((Path(__file__).parent/'fixtures/call_width.json').read_text())

def policy(minimum=8):
    result=make_policy('playbook','atk')
    result.registry.get(3,'atk','east').strategy['calls']['unsecured_opening_min_ukeire']=minimum
    return result


@pytest.mark.parametrize('case',cases())
def test_actual_narrow_opening_is_skipped_without_changing_request(case):
    req=case['request'];before=deepcopy(req);baseline=make_policy('playbook','atk')
    assert baseline.choose(req)['kind']=='pon'
    assert baseline.last_analysis['shanten']==1 and baseline.last_analysis['effective_ukeire']==7
    candidate=policy();assert candidate.choose(req)=={'kind':'skip'}
    notes=candidate.last_analysis['call_evaluations']
    assert any(n['rejections'].get('narrow_unsecured_opening') for n in notes)
    assert req==before


def test_minimum_is_an_inclusive_copy_threshold():
    req=cases()[0]['request']
    assert policy(7).choose(req)['kind']=='pon'
    assert policy(8).choose(req)['kind']=='skip'


def test_fast_legal_tenpai_is_not_blocked_by_the_opening_filter():
    candidate=policy(999);action=candidate.choose(safe_pair_wait())
    assert action['kind']=='pon' and candidate.last_analysis['shanten']==0


def test_value_call_securing_yaku_is_not_blocked_even_when_unready():
    report=sanma('9m55z4556p346789s');s=report['state'];s['turn']=1
    s['discards'][1]=[{'tile':'5z','called':False}];s['visible_tile_counts']['5z']+=1
    s['operations']={'seat':0,'operation_list':[{'type':3,'combination':['5z|5z']}]}
    report['last_event']={'name':'ActionDiscardTile','step':s['step']}
    candidate=policy(999);action=candidate.choose(decision_request(report,now=0))
    assert action['kind']=='pon'
    assert candidate.last_analysis['shanten']==1


def test_setting_does_not_change_yonma_or_south_defaults():
    candidate=policy();normal=make_policy('playbook','atk')
    assert not normal.registry.get(3,'atk','east').strategy['calls'].get('unsecured_opening_min_ukeire')
    assert not candidate.registry.get(4,'atk','east').strategy['calls'].get('unsecured_opening_min_ukeire')
    assert not candidate.registry.get(4,'atk','south').strategy['calls'].get('unsecured_opening_min_ukeire')


def test_later_call_does_not_reapply_the_first_opening_filter():
    report=sanma('1155p666s123z');s=report['state']
    s['melds'][0]=[{'type':1,'tiles':['9m']*3}];s['visible_tile_counts']['9m']=3;s['turn']=1
    s['discards'][1]=[{'tile':'1p','called':False}];s['visible_tile_counts']['1p']+=1
    s['operations']={'seat':0,'operation_list':[{'type':3,'combination':['1p|1p']}]}
    report['last_event']={'name':'ActionDiscardTile','step':s['step']}
    candidate=policy(999)
    assert candidate.choose(decision_request(report,now=0))['kind']=='pon'
    assert candidate.last_analysis['shanten']==1
