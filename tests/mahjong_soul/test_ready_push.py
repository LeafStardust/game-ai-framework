"""Narrow offline push exposure from actual East Tenpai folds."""
import json
from copy import deepcopy
from pathlib import Path
import pytest
from agents.mahjong_soul.policy import make_policy


def cases():
    return list(json.loads((Path(__file__).parent/'fixtures/ready_push.json').read_text()).values())


def candidate():
    policy=make_policy('playbook','atk')
    policy.registry.get(3,'atk','east').strategy['defense'].update(
        ready_push_max_danger=90,ready_push_min_ukeire=3)
    return policy


@pytest.mark.parametrize('case',cases())
def test_recorded_ready_push_changes_real_fold_without_mutating_board(case):
    request=case['request'];before=deepcopy(request)
    baseline=make_policy('playbook','atk');baseline.choose(request)
    assert baseline.last_analysis['mode']=='fold' and baseline.last_analysis['shanten']>0
    policy=candidate()
    assert policy.choose(request)=={'kind':'discard','tile':'7p'}
    assert policy.last_analysis['mode']=='attack_push'
    assert policy.last_analysis['shanten']==0
    assert policy.last_analysis['wait_value']['dama_ukeire']>=3
    assert request==before


@pytest.mark.parametrize('blocker',['furiten','two_threats','late_wall','two_copies','value','danger'])
def test_narrow_ready_candidate_retains_other_limits(blocker):
    request=deepcopy(cases()[0]['request']);board=request['observation']['board'];policy=candidate()
    defense=policy.registry.get(3,'atk','east').strategy['defense']
    if blocker=='furiten':board['self']['furiten']=True
    elif blocker=='two_threats':
        other=next(p for p in board['players'] if not p['is_self'] and p['riichi'] not in ('declared','accepted'))
        other['riichi']='accepted'
    elif blocker=='late_wall':board['wall_remaining']=3
    elif blocker=='two_copies':board['visible_tile_counts']['7s']=2
    elif blocker=='value':defense['ready_push_min_points']=13000
    else:defense['ready_push_max_danger']=89
    policy.choose(request)
    assert policy.last_analysis['mode']=='fold'
