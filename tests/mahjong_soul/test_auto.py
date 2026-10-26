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
    # This fixture contains tile samples only; modal checks use full-region fixtures.
    monkeypatch.setattr(vision,'require_gameplay',lambda *args,**kwargs:None)
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
    assist_calls=[]
    f.assist_buttons.poll=lambda *args,**kwargs:assist_calls.append(kwargs)
    original=f._plan;attempts=[]
    def plan(event):
        attempts.append(event)
        if len(attempts)==1: raise ValueError('Drawing animation')
        return original(event)
    f._plan=plan
    assert f.poll()['reason']=='waiting_for_stable_visuals' and not m.clicks
    # Exactly the mandatory pre-action check; no optional R/K setup on failure.
    assert assist_calls==[{"prepare_optional":False}]
    assert f.poll()['kind']=='submitted' and len(m.clicks)==1
    assert assist_calls==[{"prepare_optional":False}]*2


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


def test_live_follower_retries_timeout_once_then_accepts_late_confirmation(monkeypatch):
    from types import SimpleNamespace
    from pathlib import Path
    f,r,p,e,m=setup(monkeypatch);now=[1];f.clock=lambda:now[0]
    f.path=Path("unused");f.identity=(1,2);f.tail=SimpleNamespace(reset=False)
    f.reader=SimpleNamespace(snapshot=lambda:r);f._passive_frame=lambda _:None
    monkeypatch.setattr("agents.mahjong_soul.shadow.ShadowFollower.poll",lambda _:e)
    assert f.poll()["kind"]=="submitted" and len(m.clicks)==1
    now[0]=8
    assert f.poll()["reason"]=="awaiting_late_confirmation" and len(m.clicks)==2
    now[0]=15
    assert f.poll()["reason"]=="awaiting_late_confirmation" and len(m.clicks)==2 and f.halted is None
    assert f.controller.observe(r["game_connection"],{"name":"ActionDiscardTile","source":"live","step":r["state"]["step"]+1,"data":{"seat":r["state"]["seat"],"tile":"0p"}},now=16)
    assert f.controller.snapshot()["status"]=="idle" and f.halted is None


def test_recorded_riichi_highlights_red_and_normal_five(monkeypatch):
    import json,base64
    from pathlib import Path
    d=json.loads((Path(__file__).parent/"fixtures/riichi_red_normal_five.json").read_text())
    monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.decode_frame",lambda _:b"unused")
    def run(allowed):
        values=iter(base64.b64decode(v) for v in d["samples"])
        monkeypatch.setattr("games.mahjong_soul.live.runtime.visual.sample",lambda *args:next(values))
        return TileVision().riichi_hand(b"frame",{"slots":[(.5,.5)]*14},d["hand"],allowed)
    tiles,values,bright=run(d["allowed"])
    assert set(bright)=={"1p","0p","5p","7p"} and "0p" in tiles
    with pytest.raises(ValueError,match="Bright Riichi"):
        run(["1p","0p"])


def test_action_poll_omits_redundant_passive_frame_but_keeps_preflight(monkeypatch):
    f,r,p,e,m=setup(monkeypatch)
    monkeypatch.setattr('agents.mahjong_soul.shadow.ShadowFollower.poll',lambda _:e)
    f._passive_frame=lambda _:pytest.fail('Action preflight provides the recording')
    frames=[]
    f.recorder.frame=lambda geometry:frames.append(geometry) or b'frame'
    assert f.poll()['kind']=='submitted'
    assert len(frames)==2 and len(m.clicks)==1


def failed_focus_input(monkeypatch):
    from types import SimpleNamespace
    f,r,p,e,m=setup(monkeypatch);logs=[]
    f.reader=SimpleNamespace(snapshot=lambda:deepcopy(r))
    f._record=lambda kind,**data:logs.append((kind,data))
    def fail(*args):raise ValueError("Mahjong Soul is not the foreground window")
    m.double_click=fail
    plan,current=f._plan(e)
    with pytest.raises(ValueError):f.controller.submit(plan,current,enabled=True,now=1)
    f.halted="Mahjong Soul is not the foreground window"
    return f,r,e,m,logs


def test_focus_failure_resumes_only_after_newer_board_visual_verification(monkeypatch):
    f,r,e,m,logs=failed_focus_input(monkeypatch)
    assert not f._recover_advanced_input() and f.halted
    r["state"]["step"]+=2
    assert f._recover_advanced_input()
    assert f.halted is None and f.controller.snapshot()["status"]=="idle"
    assert not m.clicks and f.controller.was_attempted(r,0)
    assert logs[-1][1]["confirmation"]=="newer_board_visually_verified"


def test_newer_board_with_unverified_visuals_keeps_waiting(monkeypatch):
    f,r,e,m,logs=failed_focus_input(monkeypatch);r["state"]["step"]+=2
    f.recorder.geometry=lambda:None
    assert not f._recover_advanced_input()
    assert f.controller.snapshot()["status"]=="blocked" and not m.clicks


def test_server_round_end_retires_uncertain_input_without_click(monkeypatch):
    f,r,e,m,logs=failed_focus_input(monkeypatch)
    r["state"].update(status="round_ended",step=5);r["state_ready"]=False
    r["last_event"]={"name":"ActionHule","step":5}
    assert f._recover_advanced_input()
    assert f.controller.snapshot()["status"]=="idle" and not m.clicks
    assert logs[-1][1]["confirmation"]=="server_round_ended"


def test_poll_automatically_resumes_and_submits_only_the_new_step(monkeypatch):
    from pathlib import Path
    f,r,e,m,logs=failed_focus_input(monkeypatch)
    from types import SimpleNamespace
    f.path=Path("unused");f.identity=(1,2);f.source=(f.path,f.identity)
    f.tail=SimpleNamespace(reset=False);f._drain=lambda:None
    f._passive_frame=lambda _:None
    r["state"]["step"]+=2;e["board_token"]=board_token(r)
    m.double_click=lambda *args:m.clicks.append(args)
    monkeypatch.setattr("agents.mahjong_soul.shadow.ShadowFollower.poll",lambda _:e)
    assert f.poll()["kind"]=="submitted"
    assert len(m.clicks)==1 and f.halted is None
    assert f.controller.snapshot()["attempted_steps"]==2
    assert any(k=="input_recovered" for k,_ in logs)


def test_timeout_recovery_preserves_already_considered_new_turn(monkeypatch):
    from pathlib import Path
    from types import SimpleNamespace
    f,r,p,e,m=setup(monkeypatch)
    f.reader=SimpleNamespace(snapshot=lambda:deepcopy(r))
    plan,current=f._plan(e);f.controller.submit(plan,current,enabled=True,now=1)
    assert f.controller.update(r,now=10)["status"]=="blocked"
    f.path=Path("unused");f.identity=(1,2);f.source=(f.path,f.identity)
    f.tail=SimpleNamespace(reset=False)
    r["state"]["step"]+=2;e["board_token"]=board_token(r)
    events=iter([e,{"kind":"status","reason":"board_already_considered"}])
    monkeypatch.setattr("agents.mahjong_soul.shadow.ShadowFollower.poll",lambda _:next(events))
    assert f.poll()["reason"]=="input_recovered"
    assert f.poll()["kind"]=="submitted" and len(m.clicks)==2


@pytest.mark.parametrize("age,token,expected_frames",[(.1,True,1),(.3,True,1),(.5,True,1),(.51,True,2),(-.1,True,2),(.1,False,2)])
def test_fresh_assist_frame_reuse_still_captures_distinct_second_frame(monkeypatch,age,token,expected_frames):
    f,r,p,e,m=setup(monkeypatch);captured=[]
    f.assist_frame=(b"assist",f.recorder.geometry(),e["board_token"] if token else "old",1-age)
    f.recorder.frame=lambda geometry:captured.append(geometry) or b"fresh"
    f._plan(e)
    assert len(captured)==expected_frames and not m.clicks


def test_assists_are_prepared_between_turns_before_next_recommendation(monkeypatch):
    from types import SimpleNamespace
    from tests.mahjong_soul.test_sanma_east_speed import sanma
    f,_,_,_,m=setup(monkeypatch);r=sanma("19m123p456p789s112z")
    r["state"]["operations"]=None
    f.reader=SimpleNamespace(snapshot=lambda:r);calls=[]
    f.assist_buttons.poll=lambda owner,desired:calls.append(dict(desired)) or None
    monkeypatch.setattr("agents.mahjong_soul.shadow.ShadowFollower.poll",lambda _:{"kind":"status","reason":"waiting_for_offer"})
    assert f.poll()["kind"]=="status"
    assert calls and calls[0]["auto_win"] and calls[0]["auto_kita"]
    assert not m.clicks


def test_reused_first_frame_still_rejects_changed_fresh_hand(monkeypatch):
    f,r,p,e,m=setup(monkeypatch)
    f.assist_frame=(b"assist",f.recorder.geometry(),e["board_token"],.6)
    captured=[];f.recorder.frame=lambda geometry:captured.append(geometry) or b"fresh"
    f.vision.hand=lambda png,profile,expected:(list(expected),[bytes([0 if png==b"assist" else 9])*648]*len(expected))
    with pytest.raises(ValueError,match="still moving"):f._plan(e)
    assert len(captured)==1 and not m.clicks


def test_reused_first_frame_rejects_changed_window_geometry(monkeypatch):
    f,r,p,e,m=setup(monkeypatch)
    geometry=f.recorder.geometry();geometry["left"]=100
    f.assist_frame=(b"assist",geometry,e["board_token"],.6)
    captured=[];f.recorder.frame=lambda geometry:captured.append(geometry) or b"fresh"
    f._plan(e)
    assert len(captured)==2 and not m.clicks


def test_fast_recorder_png_preserves_every_channel_and_scanline():
    pattern=bytes(v for n in range(256) for v in (n,255-n,(n*13)%256,73))
    pixels=pattern*8100  # Exactly 1920 x 1080 BGRA pixels.
    expected=bytes(v for n in range(256) for v in ((n*13)%256,255-n,n))*8100
    assert decode_frame(png_from_bgra(pixels,1920,1080))==expected


def test_kan_only_offer_uses_verified_label_and_correlated_confirmation(monkeypatch):
    f,r,p,e,m=setup(monkeypatch)
    r["state"]["hand"]=["1p"]*4
    r["state"]["operations"]={"seat":0,"operation_list":[{"type":4,"combination":["1p|1p|1p|1p"]}]}
    event={"board_token":board_token(r),"action":{"kind":"closed_kan","combination":"1p|1p|1p|1p"}}
    plan,current=f._plan(event)
    f.controller.submit(plan,current,enabled=True,now=1)
    assert len(m.clicks)==1
    assert f.controller.observe(r["game_connection"],{"name":"ActionAnGangAddGang","source":"live","step":plan.step+1,
                                 "data":{"seat":0,"type":3,"tiles":"1p"}},now=2)


def test_selected_retry_hint_binds_to_pending_discard_slot_only(monkeypatch):
    f,r,p,e,m=setup(monkeypatch)
    hints=[]
    f.vision.hand=lambda png,profile,expected:(hints.append(profile.get("retry_selected_slot")) or list(expected),[bytes(648)]*len(expected))
    plan,current=f._plan(e);f.controller.submit(plan,current,enabled=True,now=1)
    f.controller.update(r,now=10);f.clock=lambda:10
    retry,current=f._plan(e)
    assert hints[:2]==[None,None] and hints[2:]==[0,0]
    f.controller.retry_discard(retry,current,visually_verified=True,enabled=True,now=10)
    assert len(m.clicks)==2
    assert f.controller.snapshot()["retry_count"]==1
