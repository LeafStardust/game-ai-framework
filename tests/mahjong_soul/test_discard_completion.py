"""Bounds and fallbacks of the experimental early discard ranking."""
from copy import deepcopy
import json
from pathlib import Path
from agents.mahjong_soul.attack_policy import enrich,offensive,attack_utility
from agents.mahjong_soul.attack_value import own_player
from agents.mahjong_soul.discard_completion import choose_completion_discard
from agents.mahjong_soul.efficiency import rank_discards
from games.mahjong_soul.playbook.sanma.east_speed import three_player_east_speed_playbook


def position():
    req=json.loads((Path(__file__).parent/'fixtures/call_width.json').read_text())[0]['request']
    board=deepcopy(req['observation']['board'])
    board['self']['hand'].append('1z');board['visible_tile_counts']['1z']=board['visible_tile_counts'].get('1z',0)+1
    board['self']['drawn_tile']='1z'
    req={'observation':{'board':board},'actions':[{'kind':'discard','tile':t} for t in sorted(set(board['self']['hand']))]}
    settings=three_player_east_speed_playbook().thresholds_for('D1')
    options=enrich(board,rank_discards(req),settings)
    key=lambda o:(-o['shanten'],o['effective_ukeire'],-o['danger'],-o['total_danger'],o['projected_han'],attack_utility(o,settings))
    return board,options,key,settings


def test_real_position_forecasts_use_only_public_state_and_preserve_shanten():
    board,options,key,settings=position();original=deepcopy(board)
    baseline=offensive(board,options,settings);assert baseline['shanten']==2
    settings['discard_completion']=True;chosen=offensive(board,options,settings)
    evaluated=[o for o in options if 'completion_estimate' in o]
    assert 2<=len(evaluated)<=3
    assert all(o['completion_estimate']['available'] for o in evaluated)
    assert chosen['shanten']==baseline['shanten']
    assert board==original


def test_unavailable_alternative_does_not_bias_the_selection():
    board,options,key,_=position();baseline=max(options,key=key);calls=[]
    def estimate(*a,**kw):
        calls.append(True)
        return {'available':False,'reason':'state_budget'} if len(calls)==2 else {'available':True,'capped_draw_cost':1}
    assert choose_completion_discard(board,options,key,estimator=estimate) is baseline


def test_worse_shanten_is_never_forecast_or_selected():
    board,options,key,_=position();baseline=max(options,key=key);other=deepcopy(baseline)
    other['action']={'kind':'discard','tile':next(t for t in board['self']['hand'] if t!=baseline['action']['tile'])}
    other['shanten']=3
    def fail(*a,**kw):raise AssertionError('Excluded choice was evaluated')
    assert choose_completion_discard(board,[baseline,other],key,estimator=fail) is baseline


def test_remaining_wall_bounds_the_horizon_and_avoids_impossible_short_search():
    board,options,key,_=position();board['wall_remaining']=5;baseline=max(options,key=key)
    def fail(*a,**kw):raise AssertionError('Not enough draws for three-step completion')
    assert choose_completion_discard(board,options,key,estimator=fail) is baseline


def test_threat_or_open_hand_does_not_run_expensive_forecasts():
    def fail(*a,**kw):raise AssertionError('Protected position was evaluated')
    for kind in ('threat','open'):
        board,options,key,_=position();baseline=max(options,key=key)
        if kind=='threat':next(p for p in board['players'] if not p['is_self'])['riichi']='accepted'
        else:own_player(board)['melds']=[{'type':1,'tiles':['5z']*3}]
        assert choose_completion_discard(board,options,key,estimator=fail) is baseline


def test_generated_legal_position_changes_decision_at_equal_shanten():
    fixture=json.loads((Path(__file__).parent/'fixtures/discard_completion.json').read_text())
    board=fixture['board'];original=deepcopy(board);options=deepcopy(fixture['options'])
    settings=three_player_east_speed_playbook().thresholds_for('D1')
    assert offensive(board,options,settings)['action']==fixture['baseline']
    settings['discard_completion']=True;chosen=offensive(board,options,settings)
    assert chosen['action']==fixture['candidate']
    baseline=next(o for o in options if o['action']==fixture['baseline'])
    assert chosen['shanten']==baseline['shanten']==2
    assert chosen['completion_estimate']['capped_draw_cost']<baseline['completion_estimate']['capped_draw_cost']
    assert chosen['completion_baseline_action']==fixture['baseline']
    assert board==original


def test_equivalent_honors_do_not_crowd_the_shortlist():
    from collections import Counter
    fixture=json.loads((Path(__file__).parent/'fixtures/early_development.json').read_text())
    board=fixture['board'];board['self']['hand'].remove('5z');board['self']['hand'].append('3z')
    board['visible_tile_counts']=dict(Counter(board['self']['hand']));board['dora_indicators']=[]
    for p in board['players']:p['discards']=[];p['melds']=[];p['riichi']='none'
    request={'observation':{'board':board},'actions':[{'kind':'discard','tile':t} for t in sorted(set(board['self']['hand']))]}
    settings=three_player_east_speed_playbook().thresholds_for('D1');options=enrich(board,rank_discards(request),settings)
    key=lambda o:(-o['shanten'],o['effective_ukeire'],-o['danger'],-o['total_danger'],o['projected_han'],attack_utility(o,settings))
    calls=[];before=Counter(board['self']['hand'])
    def estimate(after,**kwargs):
        calls.extend((before-Counter(after['self']['hand'])).elements())
        return {'available':True,'capped_draw_cost':9}
    choose_completion_discard(board,options,key,estimator=estimate)
    assert len(calls)<=3
    assert ('1z' in calls)+('2z' in calls)==1


def test_recorded_native_choice_is_reproduced_by_the_complete_policy():
    from agents.mahjong_soul.policy import make_policy
    fixture=json.loads((Path(__file__).parent/'fixtures/discard_completion_native.json').read_text())
    request=fixture['request'];original=deepcopy(request)
    normal=make_policy('playbook','atk');candidate=make_policy('playbook','atk')
    candidate.registry.get(3,'atk','east').strategy['discard_value']['discard_completion']=True
    assert normal.choose(request)==fixture['baseline']
    assert candidate.choose(request)==fixture['candidate']
    assert any('completion_estimate' in note for note in candidate.last_analysis['discard_evaluations'])
    assert request==original
