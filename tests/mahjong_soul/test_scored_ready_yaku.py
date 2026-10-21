"""A recorded pair wait earns its Yaku on the winning tile, not before it."""
from copy import deepcopy
import pytest
from agents.mahjong_soul.policy import make_policy
from games.mahjong_soul.live.runtime.decision import decision_request
from games.mahjong_soul.playbook.yonma.east_speed import east_speed_playbook
from games.mahjong_soul.playbook.yonma.south_attack import south_attack_playbook
from tests.mahjong_soul.test_sanma_ready_calls import recorded


def safe_pair_wait():
    # Derived from session 20261020T062747-902083Z, frame 818. The actual
    # 3 Pin was dangerous. Add a public Genbutsu discard to isolate the Yaku
    # gate; this is a counterfactual regression, not a missed recorded win.
    request=decision_request(recorded(818),now=0)
    board=request['observation']['board']
    board['players'][0]['discards'].insert(0,{'tile':'3p','called':False})
    board['visible_tile_counts']['3p']+=1
    return request


def test_east_calls_safe_dragon_pair_wait_with_exact_legal_yaku():
    request=safe_pair_wait();before=deepcopy(request);policy=make_policy('playbook','atk')
    action=policy.choose(request);analysis=policy.last_analysis
    assert action['kind']=='pon' and action['called_tile']=='2p'
    assert analysis['post_call_discard']=={'kind':'discard','tile':'3p'}
    assert analysis['shanten']==0 and analysis['danger']==0
    assert analysis['effective_ukeire']==4
    assert analysis['wait_value']['dama_points']==2000
    assert {w['tile'] for w in analysis['wait_value']['waits']}=={'5z','7z'}
    assert request==before


@pytest.mark.parametrize('blocker',['danger','furiten','dead_wait','value','old_gate'])
def test_exact_yaku_proof_does_not_override_other_push_gates(blocker):
    request=safe_pair_wait();board=request['observation']['board'];policy=make_policy('playbook','atk')
    defense=policy.registry.get(3,'atk','east').strategy['defense']
    if blocker=='danger':
        board['players'][0]['discards'].pop(0);board['visible_tile_counts']['3p']-=1
    elif blocker=='furiten':board['self']['furiten']=True
    elif blocker=='dead_wait':board['visible_tile_counts'].update({'5z':4,'7z':4})
    elif blocker=='value':defense['ready_push_min_points']=3000
    else:defense['allow_scored_ready_yaku']=False
    assert policy.choose(request)['kind']=='skip'


def test_scored_ready_yaku_setting_is_east_only():
    assert east_speed_playbook().strategy['defense']['allow_scored_ready_yaku']
    assert not south_attack_playbook().strategy['defense'].get('allow_scored_ready_yaku',False)


def test_four_player_east_also_accepts_legal_pair_wait():
    from tests.mahjong_soul.test_east_speed import east
    from tests.mahjong_soul.test_attack_v2 import call_report,choose
    report=east(call_report('22p3p789p888s55z77z','2p','2p|2p'))
    state=report['state'];state['riichi'][3]='accepted'
    state['discards'][3].insert(0,{'tile':'3p','called':False})
    state['visible_tile_counts']['3p']+=1
    action,analysis=choose(report)
    assert action['kind']=='pon'
    assert analysis['playbook']=='Four-Player East Speed'
    assert analysis['post_call_discard']=={'kind':'discard','tile':'3p'}
    assert analysis['shanten']==0 and analysis['danger']==0
    assert analysis['wait_value']['dama_ukeire']==4
