from copy import deepcopy
from dataclasses import replace
import pytest

from agents.mahjong_soul.auto import AutoFollower
from games.mahjong_soul.live.runtime.controller import InputController
from games.mahjong_soul.live.runtime.input import board_token, plan_discard
from games.mahjong_soul.live.runtime.visual import TileVision, decode_frame, distance
from games.mahjong_soul.live.runtime.windows_recording import png_from_bgra
from tests.mahjong_soul.test_input import inputs


class Mouse:
    def __init__(self): self.clicks=[]
    def double_click(self,*args): self.clicks.append(args)
    def click(self,*args): self.clicks.append(args)
    def park(self,*args): pass


class Recorder:
    def geometry(self): return {"width":1920,"height":1080,"left":0,"top":0}
    def frame(self,geometry): return b"frame"


class Vision:
    def hand(self,png,profile,expected): return list(expected),[bytes(648)]*len(expected)
    def skip_visible(self,png,profile): return bytes(648)
    def button(self,png,kind,point=None):return (1290 if kind=="skip" else 1020),835,bytes(648)
    def riichi_hand(self,png,profile,expected,allowed):return list(expected),[bytes(648)]*len(expected),list(allowed)


def setup(monkeypatch):
    report,profile=inputs();profile['client_size']=[1920,1080]
    mouse=Mouse()
    follower=AutoFollower(None,file='unused',controller=InputController(mouse),recorder=Recorder(),vision=Vision(),enabled=True,clock=lambda:1,sleep=lambda _:None)
    follower._current=lambda:deepcopy(report)
    monkeypatch.setattr('agents.mahjong_soul.auto.discard_profile',lambda *args:profile)
    event={'kind':'suggestion','action':{'kind':'discard','tile':'0p'},'board_token':board_token(report)}
    return follower,report,profile,event,mouse


def test_visual_plan_uses_recognized_slot_and_atomic_double_click(monkeypatch):
    f,r,p,e,m=setup(monkeypatch)
    plan,current=f._plan(e)
    assert plan.double_click
    f.controller.submit(plan,current,enabled=True,now=1)
    assert len(m.clicks)==1
    with pytest.raises(ValueError,match='pending'): f.controller.submit(plan,current,enabled=True,now=1)
    assert f.controller.observe('game',{'name':'ActionDiscardTile','source':'live','step':1,'data':{'seat':0,'tile':'0p'}},now=2)
    assert f.controller.snapshot()['status']=='idle'


@pytest.mark.parametrize('failure',['wrong_board','wrong_size','moved','no_frame','unknown_tile','animation','changed_during_visuals'])
def test_preflight_failures_never_send_input(monkeypatch,failure):
    f,r,p,e,m=setup(monkeypatch)
    if failure=='wrong_board': e['board_token']='old'
    elif failure=='wrong_size': f.recorder.geometry=lambda:{'width':1920,'height':1200}
    elif failure=='moved':
        calls=iter([{'width':1920,'height':1080,'left':0,'top':0},{'width':1920,'height':1080,'left':1,'top':0}])
        f.recorder.geometry=lambda:next(calls)
    elif failure=='no_frame': f.recorder.frame=lambda _:None
    elif failure=='unknown_tile':
        def reject(*args): raise ValueError('Unknown tile')
        f.vision.hand=reject
    elif failure=='animation':
        values=iter([(['0p'],[bytes(648)]),(['0p'],[bytes([9])*648])])
        f.vision.hand=lambda *args:next(values)
    else:
        def advance(_): r['state']['step']+=1
        f.sleep=advance
    with pytest.raises(ValueError): f._plan(e)
    assert not m.clicks


def test_rpc_and_action_events_forward_to_persistent_controller(monkeypatch):
    f,r,p,e,m=setup(monkeypatch)
    calls=[]
    class Reader:
        def consume(self,row): return {'liqi':{'events':[{'name':'action'}]}}
    f.reader=Reader()
    f.controller.observe=lambda *args,**kw:calls.append(('event',args))
    f.controller.observe_message=lambda *args,**kw:calls.append(('rpc',args))
    f._consume({'connection':'game','direction':'client'})
    assert calls==[('event',('game',{'name':'action'})),('rpc',('game',{'events':[{'name':'action'}]},True))]


def test_visual_bank_distinguishes_every_reviewed_label_and_rejects_unknown():
    vision=TileVision()
    assert len(set(tile for tile,_ in vision.tiles))==37
    for tile,value in vision.tiles: assert vision.classify(value)==tile
    with pytest.raises(ValueError): vision.classify(bytes(648))
    with pytest.raises(ValueError): distance(b'bad',b'bad')


def test_recorder_png_decoder_rejects_corruption_and_other_sizes():
    png=png_from_bgra(bytes([1,2,3,255])*1920*1080,1920,1080)
    rgb=decode_frame(png)
    assert rgb[:6]==bytes([3,2,1,3,2,1])
    corrupt=bytearray(png);corrupt[-6]^=1
    with pytest.raises(ValueError): decode_frame(bytes(corrupt))
    with pytest.raises(ValueError): decode_frame(png[:-10])
    with pytest.raises(ValueError): decode_frame(png_from_bgra(bytes(16),2,2))


def test_poll_dry_mode_never_reads_screen_or_inputs(monkeypatch):
    f,r,p,e,m=setup(monkeypatch);f.enabled=False
    monkeypatch.setattr('agents.mahjong_soul.shadow.ShadowFollower.poll',lambda _:e)
    f._plan=lambda _:pytest.fail('No screen reads in dry mode')
    assert f.poll()==e and not m.clicks


def test_poll_manual_actions_are_not_substituted(monkeypatch):
    f,r,p,e,m=setup(monkeypatch);e['action']={'kind':'abortive_draw'}
    monkeypatch.setattr('agents.mahjong_soul.shadow.ShadowFollower.poll',lambda _:e)
    result=f.poll()
    assert result['kind']=='manual' and result['action']==e['action'] and not m.clicks


def test_poll_partial_delivery_blocks_without_retry(monkeypatch):
    f,r,p,e,m=setup(monkeypatch)
    monkeypatch.setattr('agents.mahjong_soul.shadow.ShadowFollower.poll',lambda _:e)
    def fail(*args): m.clicks.append(args);raise OSError('Partial delivery')
    m.double_click=fail
    assert f.poll()['kind']=='blocked'
    assert f.poll()['kind']=='blocked'
    assert len(m.clicks)==1


def test_independent_recorded_hand_has_correct_visual_order(monkeypatch):
    import base64,json
    from pathlib import Path
    fixture=json.loads((Path(__file__).parent/'fixtures/visual_hand.json').read_text(encoding='utf-8'))
    vision=TileVision()
    values=[base64.b64decode(value) for value in fixture['samples']]
    assert [vision.classify(value) for value in values]==fixture['expected']
    monkeypatch.setattr('games.mahjong_soul.live.runtime.visual.decode_frame',lambda _:b'pixels')
    samples=iter(values)
    monkeypatch.setattr('games.mahjong_soul.live.runtime.visual.sample',lambda *args:next(samples))
    profile={'client_size':[1920,1080],'slots':[[.5,.9]]*14}
    actual,_=vision.hand(b'frame',profile,list(reversed(fixture['expected'])))
    assert actual==fixture['expected']  # Reader order cannot determine visual slot.
    samples=iter(values)
    with pytest.raises(ValueError,match='differs from reader'):
        vision.hand(b'frame',profile,['1z']*14)


def test_visual_stabilization_reuses_one_decision_without_reclicking(monkeypatch):
    f,r,p,e,m=setup(monkeypatch)
    events=iter([e,{'kind':'status','reason':'board_already_considered'}])
    monkeypatch.setattr('agents.mahjong_soul.shadow.ShadowFollower.poll',lambda _:next(events))
    class Reader:
        def snapshot(self): return r
    f.reader=Reader()
    original=f._plan;attempts=[]
    def plan(event):
        attempts.append(event)
        if len(attempts)==1: raise ValueError('Drawing animation')
        return original(event)
    f._plan=plan
    assert f.poll()['reason']=='waiting_for_stable_visuals' and not m.clicks
    assert f.poll()['kind']=='submitted' and len(m.clicks)==1


def test_timeout_blocks_next_action(monkeypatch):
    f,r,p,e,m=setup(monkeypatch)
    monkeypatch.setattr('agents.mahjong_soul.shadow.ShadowFollower.poll',lambda _:e)
    assert f.poll()['kind']=='submitted'
    f.controller.update(r,now=10)
    # Once an attempted action becomes uncertain the same controller blocks submission.
    assert f.poll()['kind']=='blocked' and len(m.clicks)==1


@pytest.mark.parametrize('codes',[[3],[2,3],[3,5],[2,3,5]])
def test_skip_uses_visible_button_for_every_supported_call_offer(monkeypatch,codes):
    f,r,p,e,m=setup(monkeypatch)
    r['state']['operations']['operation_list']=[{'type':code} for code in codes]
    e.update(board_token=board_token(r),action={'kind':'skip'})
    plan,current=f._plan(e)
    f.controller.submit(plan,current,enabled=True,now=1)
    assert len(m.clicks)==1


@pytest.mark.parametrize('kind',['ron','tsumo'])
def test_runner_executes_win_instead_of_discarding(monkeypatch,kind):
    f,r,p,e,m=setup(monkeypatch)
    if kind=='ron':
        from tests.mahjong_soul.test_calls import chi_offer
        r,_=chi_offer();r['state']['operations']={'seat':0,'operation_list':[{'type':3},{'type':9}]}
    else:
        r['state']['drawn_tile']='0p'
        r['state']['operations']['operation_list'].append({'type':8})
    f._current=lambda:deepcopy(r)
    e.update(board_token=board_token(r),action={'kind':kind})
    plan,current=f._plan(e);f.controller.submit(plan,current,enabled=True,now=1)
    assert len(m.clicks)==1
    assert f.controller.snapshot()['status']=='awaiting_confirmation'


def test_runner_riichi_is_automatic_and_waits_for_acceptance(monkeypatch):
    f,r,p,e,m=setup(monkeypatch)
    r['state']['operations']['operation_list'].append({'type':7,'combination':['0p']})
    e.update(board_token=board_token(r),action={'kind':'riichi','tile':'0p'})
    monkeypatch.setattr('agents.mahjong_soul.shadow.ShadowFollower.poll',lambda _:e)
    result=f.poll();assert result['kind']=='submitted' and len(m.clicks)==1
    f._continue_riichi();assert len(m.clicks)==2
    assert f.controller.riichi_phase()=='awaiting_declaration'
    f._continue_riichi();assert len(m.clicks)==2
    from tests.mahjong_soul.test_riichi import declaration
    assert not f.controller.observe('game',declaration(),now=2)
    assert f.controller.observe('game',{'name':'ActionDealTile','source':'live','step':2,'data':{'liqi':{'seat':0,'score':24000}}},now=2)


def test_riichi_menu_mismatch_cannot_send_discard(monkeypatch):
    f,r,p,e,m=setup(monkeypatch)
    r['state']['operations']['operation_list'].append({'type':7,'combination':['0p']})
    e.update(board_token=board_token(r),action={'kind':'riichi','tile':'0p'})
    monkeypatch.setattr('agents.mahjong_soul.shadow.ShadowFollower.poll',lambda _:e)
    f.poll()
    f.vision.riichi_hand=lambda *args:(['0p'],[bytes(648)],['5p'])
    with pytest.raises(ValueError,match='match'):f._continue_riichi()
    assert len(m.clicks)==1



@pytest.mark.parametrize("duplicates",[False,True])
def test_recorded_riichi_menu_distinguishes_allowed_tiles_from_dimmed_tiles(monkeypatch,duplicates):
    import json,base64
    from pathlib import Path
    fixture=json.loads((Path(__file__).parent/'fixtures/visual_riichi.json').read_text(encoding='utf-8'))
    values=[base64.b64decode(v) for v in fixture['samples']]
    monkeypatch.setattr('games.mahjong_soul.live.runtime.visual.decode_frame',lambda _:b'pixels')
    samples=iter(values)
    monkeypatch.setattr('games.mahjong_soul.live.runtime.visual.sample',lambda *args:next(samples))
    profile={'slots':[[.5,.9]]*14}
    tiles,_,allowed=TileVision().riichi_hand(b'frame',profile,fixture['expected'],fixture['allowed']*(3 if duplicates else 1))
    assert tiles==fixture['expected'] and allowed==['3p']
    samples=iter(values)
    with pytest.raises(ValueError,match='Bright Riichi'):
        TileVision().riichi_hand(b'frame',profile,fixture['expected'],['7p'])


def test_red_five_sou_requires_five_bamboo_shape_and_red_ink():
    vision=TileVision();normal=next(value for tile,value in vision.tiles if tile=='5s')
    red=bytearray(normal)
    for i in range(0,len(red),3):
        r,g,b=red[i:i+3]
        if g>r*1.2 and g>b*1.1:red[i:i+3]=bytes([g,r,b])
    assert vision.classify(bytes(red))=='0s'
    assert vision.classify(normal)=='5s'



def test_capture_to_policy_to_native_backend_and_server_confirmation(tmp_path,monkeypatch):
    from tests.mahjong_soul.test_shadow import Reader,append,row,advance
    from agents.mahjong_soul.policy import BaselinePolicy
    from games.mahjong_soul.live.runtime.session import SessionJournal,RecordingMouse
    class EventReader(Reader):
        def consume(self,value):
            super().consume(value)
            return {'liqi':value['decoded']} if 'decoded' in value else {}
    monkeypatch.setattr('agents.mahjong_soul.shadow.GameReader',EventReader)
    report,profile=inputs();profile['client_size']=[1920,1080]
    monkeypatch.setattr('agents.mahjong_soul.auto.discard_profile',lambda *args:profile)
    path=tmp_path/'capture.jsonl';append(path,row(report))
    journal=SessionJournal(tmp_path/'sessions');mouse=Mouse()
    follower=AutoFollower(None,file=path,policy=BaselinePolicy(),controller=InputController(RecordingMouse(mouse,journal)),
        recorder=Recorder(),vision=Vision(),journal=journal,enabled=True,clock=lambda:1,wall_clock=lambda:100,sleep=lambda _:None)
    assert follower.poll()['reason']=='capture_bootstrapped' and not mouse.clicks
    report=advance(report);append(path,row(report))
    assert follower.poll()['kind']=='submitted' and len(mouse.clicks)==1
    follower.poll();assert len(mouse.clicks)==1
    done=advance(report);done['state']['operations']=None;done['state']['hand']=[]
    value=row(done);value['decoded']={'events':[{'name':'ActionDiscardTile','source':'live','step':done['state']['step'],'data':{'seat':0,'tile':'0p'}}]}
    append(path,value);follower.poll()
    assert follower.controller.snapshot()['status']=='idle'
    report['state']['step']=done['state']['step']+1;append(path,row(report))
    assert follower.poll()['kind']=='submitted' and len(mouse.clicks)==2
    journal.close()
    from agents.mahjong_soul.inspect_run import summarize
    summary=summarize(journal.directory)
    assert summary['counts']['confirmed']==1 and summary['counts']['input_attempt']==2



def test_production_ai_guard_requires_captured_authentication(monkeypatch):
    f,r,p,e,m=setup(monkeypatch);f.require_ai=True
    with pytest.raises(ValueError,match='AI opponents'):f._plan(e)
    f.ai_games.add((r['game_connection'],r.get('game_generation',0)))
    f._plan(e)
    assert not m.clicks
    r['game_generation']+=1;e['board_token']=board_token(r)
    with pytest.raises(ValueError,match='AI opponents'):f._plan(e)
