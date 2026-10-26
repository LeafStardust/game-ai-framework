from collections import Counter
from copy import deepcopy
import pytest
from agents.mahjong_soul.attack_value import tenpai_value,yaku_routes
from agents.mahjong_soul.attack_defense import danger,threats
from agents.mahjong_soul.playbook_policy import PlaybookPolicy
from agents.mahjong_soul.evaluate import decide
from games.mahjong_soul.live.runtime.decision import decision_request
from games.mahjong_soul.live.runtime.observation import observation_from_snapshot
from tests.mahjong_soul.test_efficiency import request,tiles


def report(hand,*,melds=(),doras=(),river=(),kuitan=True):
    _,r=request(hand,len(melds));s=r['state']
    s.update(round={'chang':0,'ju':0},left_tile_count=40,furiten=False,rules={'open_tanyao':kuitan})
    s['melds'][0]=deepcopy(list(melds));s['doras']=list(doras)
    s['discards'][0]=[{'tile':t,'called':False} for t in river]
    visible=s['hand']+[t for m in melds for t in m['tiles']]+list(doras)+list(river)
    s['visible_tile_counts']=dict(Counter('5'+t[1:] if t.startswith('0') else t for t in visible))
    return r


def board(*args,**kwargs):return observation_from_snapshot(report(*args,**kwargs))['board']


def call_report(hand,called,combination,code=3,**kwargs):
    r=report(hand,**kwargs);s=r['state'];s['turn']=3
    s['discards'][3]=[{'tile':called,'called':False}]
    kind='5'+called[1:] if called.startswith('0') else called
    s['visible_tile_counts'][kind]=s['visible_tile_counts'].get(kind,0)+1
    s['operations']={'seat':0,'operation_list':[{'type':code,'combination':[combination]}]}
    r['last_event']={'name':'ActionDiscardTile','step':s['step']}
    return r


def choose(r):
    policy=PlaybookPolicy(style='atk');action=decide(policy,r,lambda:r)['action']
    return action,policy.last_analysis


def test_open_dora_without_yaku_has_no_legal_scoring_wait():
    b=board('456m789p23s55p',melds=[{'type':0,'tiles':tiles('123m')}],doras=['4p'])
    value=tenpai_value(b,b['self']['hand'])
    assert value['unseen_waits']>0 and value['dama_ukeire']==value['tsumo_ukeire']==0
    assert not yaku_routes(b,b['self']['hand'])['open_yaku']


@pytest.mark.parametrize('enabled',[True,False,None])
def test_open_tanyao_scoring_requires_known_room_rule(enabled):
    b=board('234m345p67s55p',melds=[{'type':0,'tiles':tiles('456s')}],kuitan=enabled)
    value=tenpai_value(b,b['self']['hand'])
    assert bool(value['dama_ukeire'])==(enabled is True)


def test_red_five_and_indicator_dora_stack_without_inventing_ura_or_ippatsu():
    plain=board('123m123p123s789s0p');plain['self']['scoring_context']={}
    bonus=deepcopy(plain);bonus['dora_indicators']=['4p']
    first=tenpai_value(plain,plain['self']['hand']);second=tenpai_value(bonus,bonus['self']['hand'])
    a=first['waits'][0]['values'];b=second['waits'][0]['values']
    assert b['dama']['han']==a['dama']['han']+2
    assert b['riichi']['han']==b['dama']['han']+1
    assert all('Ura' not in name and 'Ippatsu' not in name for name in b['riichi']['yaku'])


def test_dead_discarded_wait_still_causes_whole_hand_furiten():
    b=board('234m345p456s23s55p',river=['1s'])
    b['visible_tile_counts']['1s']=4
    value=tenpai_value(b,b['self']['hand'])
    assert value['permanent_furiten'] and value['dama_ukeire']==0 and value['tsumo_ukeire']>0
    assert any(w['tile']=='1s' and w['unseen']==0 for w in value['waits'])


def test_concealed_red_kan_keeps_hand_closed_for_riichi_value():
    b=board('123m123p789s2z',melds=[{'type':3,'tiles':tiles('0555s')}])
    value=tenpai_value(b,b['self']['hand'])
    assert value['riichi_ukeire']>0 and value['riichi_points']>0


def test_value_honor_pon_chooses_legal_tenpai_and_preserves_input():
    r=call_report('55z123m456p78s22p9m','5z','5z|5z',doras=['1p']);before=deepcopy(r)
    action,analysis=choose(r)
    assert action['kind']=='pon' and analysis['post_call_discard']=={'kind':'discard','tile':'9m'}
    assert analysis['wait_value']['dama_ukeire']==8 and r==before


@pytest.mark.parametrize('enabled',[True,False,None])
def test_chi_opens_tanyao_only_when_the_rule_allows_it(enabled):
    r=call_report('23m234p456s67s55p9p','4m','2m|3m',2,kuitan=enabled,doras=['4p'])
    action,analysis=choose(r)
    assert action['kind']==('chi' if enabled is True else 'skip')
    if enabled is True:assert analysis['post_call_discard']['tile']=='9p'


def test_dora_does_not_justify_a_yakuless_opening():
    r=call_report('23m234p456s67s55p9p','1m','2m|3m',2,doras=['4p'])
    assert choose(r)[0]['kind']=='skip'


def test_exact_red_call_combination_is_retained():
    r=call_report('05p234m456s67s22p9m','5p','0p|5p',doras=['4p'])
    action,analysis=choose(r)
    assert action['kind']=='pon' and action['combination']=='0p|5p'
    assert analysis['value_han']>=2


def test_cheap_yakuhai_call_does_not_abandon_closed_value():
    r=call_report('55z123m456p789s12p','5z','5z|5z')
    assert choose(r)[0]['kind']=='skip'


def test_open_tenpai_keeps_pushing_into_riichi():
    r=call_report('55z123m456p78s22p9m','5z','5z|5z',doras=['1p'])
    r['state']['riichi'][1]='accepted'
    assert choose(r)[0]['kind']=='pon'


def test_chi_planning_respects_called_and_swap_discard_restrictions(monkeypatch):
    from agents.mahjong_soul.efficiency import rank_discards
    checked=[]
    def checked_rank(q):
        assert not {'1m','4m'}&{a['tile'] for a in q['actions']}
        checked.append(True);return rank_discards(q)
    monkeypatch.setattr('agents.mahjong_soul.playbook_policy.rank_discards',checked_rank)
    r=call_report('12345m456p67s55p9s','1m','2m|3m',2)
    choose(r);assert checked


def test_closed_kan_preserves_distance_and_waits_even_against_riichi():
    r=report('1111m234p567p789s2z')
    r['state']['operations']['operation_list'].append({'type':4,'combination':['1m|1m|1m|1m']})
    assert choose(r)[0]['kind']=='closed_kan'
    r['state']['riichi'][1]='accepted'
    assert choose(r)[0]['kind']=='closed_kan'


def test_late_wall_and_seven_pairs_shapes_decline_kan():
    r=report('1111m234p567p789s2z');r['state']['left_tile_count']=4
    r['state']['operations']['operation_list'].append({'type':4,'combination':['1m|1m|1m|1m']})
    assert choose(r)[0]['kind']=='discard'
    r=report('1122m3344p5555s77z')
    r['state']['operations']['operation_list'].append({'type':4,'combination':['5s|5s|5s|5s']})
    assert choose(r)[0]['kind']=='discard'


def test_suji_reduces_relative_danger_but_is_not_guaranteed_safe():
    b=board('123m456p789s111z2z');b['players'][1]['riichi']='accepted'
    b['players'][1]['discards']=[{'tile':'4m'}];t=threats(b)
    assert 0<danger(b,'1m',t)['danger']<danger(b,'9m',t)['danger']
    assert danger(b,'4m',t)['danger']==0


def test_full_attack_does_not_fold_to_multiple_opponents(monkeypatch):
    from tests.mahjong_soul.test_attack import mock_rank
    r=report('15m',melds=[{'type':1,'tiles':[str(i)+'p']*3} for i in range(2,6)])
    for seat,tile in [(1,'5m'),(2,'5m'),(3,'1m')]:
        r['state']['riichi'][seat]='accepted';r['state']['discards'][seat]=[{'tile':tile,'called':False}]
    mock_rank(monkeypatch,distance=2)
    # Replace the old 1m/2m rank fixture with actual offered 1m/5m choices.
    monkeypatch.setattr('agents.mahjong_soul.playbook_policy.rank_discards',lambda q:[
        {'action':{'kind':'discard','tile':t},'shanten':2,'ukeire':20,'improving_tiles':[]} for t in ['5m','1m']])
    action,analysis=choose(r)
    assert action['tile']=='5m' and analysis['mode']=='attack_push'


def test_open_value_threat_is_recognized_without_riichi():
    b=board('123m456p789s111z2z')
    b['players'][1]['melds']=[{'type':1,'tiles':[t]*3} for t in ['5z','3p','4s']]
    assert threats(b)[0]['threat_kind']=='open_hand'


def test_wider_wait_riichi_beats_small_point_gain_from_halving_winning_copies():
    r=report('123m123p123s111z23s',doras=['1s','1s'])
    r['state']['operations']['operation_list'].append({'type':7,'combination':['1s']})
    action,analysis=choose(r)
    assert action=={'kind':'riichi','tile':'1s'}
    assert analysis['wait_value']['dama_points']>=7700


def test_permanent_furiten_after_discard_blocks_new_riichi():
    r=report('123m456m789p23s55p7z',river=['1s'])
    r['state']['operations']['operation_list'].append({'type':7,'combination':['7z']})
    assert choose(r)[0]['kind']=='discard'


def test_ordinary_riichi_still_uses_the_offered_discard():
    r=report('123m456m789p23s55p7z')
    r['state']['operations']['operation_list'].append({'type':7,'combination':['7z']})
    assert choose(r)[0]=={'kind':'riichi','tile':'7z'}


def test_dead_tenpai_can_be_rebuilt_instead_of_waiting_for_exhausted_tiles():
    r=report('123m456p789s111z2z3z')
    r['state']['visible_tile_counts'].update({'2z':4,'3z':4})
    action,analysis=choose(r)
    assert analysis['shanten']==1 and analysis['ukeire']>0



def test_default_suggestion_monitor_prints_only_the_action(monkeypatch,capsys):
    import sys
    from types import SimpleNamespace
    from agents.mahjong_soul import shadow
    r=report('123m456m789p23s55p7z')
    action,analysis=choose(r)
    event={'kind':'suggestion','action':action,'analysis':analysis,'board_token':'test'}
    monkeypatch.setattr(shadow,'ShadowFollower',lambda *args,**kwargs:SimpleNamespace(poll=lambda:event))
    monkeypatch.setattr(sys,'argv',['shadow','--policy','playbook','--playstyle','atk','--once'])
    assert shadow.main()==0
    assert capsys.readouterr().out==shadow.format_suggestion(event)+'\n'


def test_reported_furiten_does_not_count_ron_waits_as_available():
    b=board('123m456m789p23s55p');b['self']['furiten']=True
    value=tenpai_value(b,b['self']['hand'])
    assert value['ron_blocked'] and not value['permanent_furiten']
    assert value['dama_ukeire']==0 and value['tsumo_ukeire']>0


def test_scoring_results_cannot_poison_the_cached_hand_calculator():
    b=board('123m123p123s111z2z')
    value=tenpai_value(b,b['self']['hand']);expected=value['waits'][0]['values']['dama']['han']
    value['waits'][0]['values']['dama']['han']=999
    assert tenpai_value(b,b['self']['hand'])['waits'][0]['values']['dama']['han']==expected



def test_exhausted_honors_are_not_declared_absolute_safety_against_closed_kokushi():
    b=board('123m456p789s111z2z');b['players'][1]['riichi']='accepted'
    b['visible_tile_counts']['2z']=4
    assert danger(b,'2z',threats(b))['danger']>0


def test_yakuless_closed_tenpai_can_open_when_it_enables_a_valuable_ron():
    r=call_report('55z123m456p789s12p','5z','5z|5z',doras=['7z'])
    action,analysis=choose(r)
    assert action['kind']=='pon' and analysis['wait_value']['dama_points']>=2000



def test_developed_seven_pairs_value_can_support_a_selective_push():
    r=report('1122m3344p556s7z8s9m');r['state']['riichi'][1]='accepted'
    action,analysis=choose(r)
    assert analysis['mode']=='attack_push'
    assert analysis['yaku_potential']['chiitoitsu']==2
    assert analysis['push_value_estimate']>=3



def test_a_weaker_riichi_alternative_does_not_replace_the_best_high_value_dama(monkeypatch):
    from agents.mahjong_soul import attack_policy
    original=attack_policy.tenpai_value
    def alternate_value(b,hand,*,discard=None):
        value=original(b,hand,discard=discard)
        if value and discard=='2s':value.update(dama_points=1000,riichi_points=2000)
        return value
    monkeypatch.setattr(attack_policy,'tenpai_value',alternate_value)
    r=report('123m123p123s111z23s',doras=['1s','1s'])
    r['state']['operations']['operation_list'].append({'type':7,'combination':['2s']})
    action,analysis=choose(r)
    assert action['kind']=='discard' and analysis['wait_value']['dama_points']>=7700



def test_kan_is_declined_when_it_reduces_known_tenpai_value(monkeypatch):
    from agents.mahjong_soul import attack_policy
    original=attack_policy.tenpai_value
    def after_kan_value(b,hand,*,discard=None):
        value=original(b,hand,discard=discard)
        if value and b['players'][0]['melds']:value.update(dama_points=0,riichi_points=0)
        return value
    monkeypatch.setattr(attack_policy,'tenpai_value',after_kan_value)
    r=report('1111m234p567p789s2z')
    r['state']['operations']['operation_list'].append({'type':4,'combination':['1m|1m|1m|1m']})
    assert choose(r)[0]['kind']=='discard'


@pytest.mark.parametrize("wall,threat_count,doras,expected",[
    (13,2,["3s"],"discard"),(30,2,["3s"],"riichi"),
    (13,0,["3s"],"riichi"),(13,2,[],"riichi"),
])
def test_late_two_threat_valuable_dama_keeps_attacking_without_small_gain_riichi(wall,threat_count,doras,expected):
    r=report("113355p224466s7z9p",doras=doras)
    s=r["state"];s.update(left_tile_count=wall,scoring_context={})
    for index in range(threat_count):s["riichi"][index+1]="accepted"
    s["operations"]["operation_list"].append({"type":7,"combination":["9p"]})
    action,analysis=choose(r)
    assert action=={"kind":expected,"tile":"9p"}
    assert analysis["shanten"]==0
    if expected=="discard":
        assert any(n.get("reason")=="late_valuable_dama_small_riichi_gain" for n in analysis["discard_evaluations"])


def test_riichi_kan_only_offer_does_not_enter_thirteen_tile_call_evaluation():
    r=report("1111p234p567s789s2z")
    r["state"]["riichi"][0]="accepted"
    r["state"]["drawn_tile"]="1p"
    r["state"]["operations"]={"seat":0,"operation_list":[{"type":4,"combination":["1p|1p|1p|1p"]}]}
    action,analysis=choose(r)
    assert action=={"kind":"closed_kan","combination":"1p|1p|1p|1p"}
    assert analysis["mode"]=="sole_server_closed_kan"
