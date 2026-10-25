import base64,json,zlib
from pathlib import Path
from games.mahjong_soul.live.runtime.assist_buttons import AssistButtons
from tests.mahjong_soul.test_result_buttons import owner


def panel(name="assist_panel.json"):
    data=json.loads((Path(__file__).parent/"fixtures"/name).read_text())
    x,y,w,h=data["crop"];crop=zlib.decompress(base64.b64decode(data["rgb_zlib"]));rgb=bytearray(1920*1080*3)
    for row in range(h):rgb[((y+row)*1920+x)*3:((y+row)*1920+x+w)*3]=crop[row*w*3:(row+1)*w*3]
    return rgb


def test_real_panel_states_and_unknown_panel(monkeypatch):
    rgb=panel();monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    handler=AssistButtons()
    assert handler.read(b"frame")=={"arrange":True,"auto_win":False,"skip_calls":False,"auto_discard":False,"auto_kita":False}
    rgb[:]=bytes(len(rgb))
    assert handler.read(b"frame") is None


def test_toggle_is_confirmed_without_second_click(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    now=[1];o.clock=lambda:now[0];rgb=panel()
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    handler=AssistButtons();desired={"auto_win":True,"skip_calls":False,"auto_discard":False,"auto_kita":False}
    assert handler.poll(o,desired)["reason"]=="assist_submitted" and len(m.clicks)==1
    now[0]=2
    assert handler.poll(o,desired)["reason"]=="awaiting_assist_confirmation" and len(m.clicks)==1
    for y in range(539,546):
        for x in range(57,64):rgb[(y*1920+x)*3:(y*1920+x)*3+3]=bytes(handler.profile["on"])
    now[0]=3
    assert handler.poll(o,desired) is None and len(m.clicks)==1
    assert logs[-1][0]=="assist_confirmed"


def test_toggle_rechecks_board_and_never_retries_unknown_delivery(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    now=[1];o.clock=lambda:now[0];rgb=panel()
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    handler=AssistButtons();desired={"auto_win":True,"skip_calls":False,"auto_discard":False,"auto_kita":False}
    o.sleep=lambda _:r["state"]["hand"].append("1z")
    assert handler.poll(o,desired) is None and not m.clicks
    o.sleep=lambda _:None;now[0]=2
    assert handler.poll(o,desired)["reason"]=="assist_submitted"
    now[0]=6
    assert handler.poll(o,desired) is None and len(m.clicks)==1 and not o.halted
    assert "auto_win" in handler.unavailable and handler.pending is None
    now[0]=7
    assert handler.poll(o,desired) is None and len(m.clicks)==1


def test_collapsed_letters_click_directly_and_confirm_colour(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    now=[1];o.clock=lambda:now[0];rgb=panel("assist_collapsed.json")
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    handler=AssistButtons()
    assert handler.read(b"frame")=={"arrange":True,"auto_win":False,"skip_calls":False,"auto_discard":False,"auto_kita":False}
    assert handler.layout=="collapsed"
    desired={"auto_win":True,"skip_calls":False,"auto_discard":False,"auto_kita":False}
    assert handler.poll(o,desired)["reason"]=="assist_submitted"
    assert (round(m.clicks[0][0]*1919),round(m.clicks[0][1]*1079))==(40,578)
    row=handler.profile["collapsed"]["auto_win"]
    for index in row["mask"]:
        y,x=divmod(index,37);offset=((row["y"]-24+y)*1920+21+x)*3
        rgb[offset:offset+3]=bytes(handler.profile["on"])
    now[0]=2
    assert handler.poll(o,desired) is None and len(m.clicks)==1
    assert logs[-1][0]=="assist_confirmed"


def test_collapsed_partial_colour_and_layout_changes_are_rejected(monkeypatch):
    o,r,m,_=owner(monkeypatch);r["state"].update(status="tracking",player_count=3);o.clock=lambda:1
    collapsed=panel("assist_collapsed.json");expanded=panel();calls=[collapsed,expanded]
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:calls.pop(0) if len(calls)>1 else calls[0])
    handler=AssistButtons();desired={"auto_win":True,"skip_calls":False,"auto_discard":False,"auto_kita":False}
    assert handler.poll(o,desired) is None and not m.clicks
    rgb=panel("assist_collapsed.json");row=handler.profile["collapsed"]["auto_win"]
    for index in row["mask"][:len(row["mask"])//2]:
        y,x=divmod(index,37);offset=((row["y"]-24+y)*1920+21+x)*3;rgb[offset:offset+3]=bytes(handler.profile["on"])
    assert handler.collapsed(rgb) is None


def test_actual_bright_gameplay_sidebar_is_recognized(monkeypatch):
    rgb=panel("assist_collapsed_gameplay.json")
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    handler=AssistButtons()
    assert handler.read(b"frame")=={"arrange":True,"auto_win":False,"skip_calls":False,"auto_discard":False,"auto_kita":False}
    assert handler.layout=="collapsed"


def test_expired_riichi_assist_resolves_when_next_hand_observably_unlocked(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    o.clock=lambda:10
    rgb=panel()
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    handler=AssistButtons();handler.pending=("auto_discard",True,3)
    desired={"auto_win":False,"skip_calls":False,"auto_discard":False,"auto_kita":False}
    assert handler.poll(o,desired) is None
    assert handler.pending is None and not handler.failed and not o.halted and not m.clicks
    assert logs[-1][0]=="assist_superseded"


def test_obsolete_assist_with_unreadable_state_waits_for_recovery(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    o.clock=lambda:10
    handler=AssistButtons();handler.pending=("auto_discard",True,3)
    monkeypatch.setattr(handler,"read",lambda _:None)
    desired={"auto_win":False,"skip_calls":False,"auto_discard":False,"auto_kita":False}
    assert handler.poll(o,desired)["reason"]=="waiting_for_assist_recovery"
    assert not m.clicks and o.halted


def test_switch_confirms_immediately_without_half_second_poll_delay(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    o.clock=lambda:1;rgb=panel();handler=AssistButtons()
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    original=m.click
    def click(*args):
        original(*args)
        for y in range(539,546):
            for x in range(57,64):rgb[(y*1920+x)*3:(y*1920+x)*3+3]=bytes(handler.profile["on"])
    m.click=click
    desired={"auto_win":True,"skip_calls":False,"auto_discard":False,"auto_kita":False}
    assert handler.poll(o,desired) is None
    assert handler.pending is None and len(m.clicks)==1
    assert logs[-1][0]=="assist_confirmed"


def test_unknown_auto_discard_waits_for_recovery_instead_of_guessing(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    now=[1];o.clock=lambda:now[0];rgb=panel()
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    handler=AssistButtons();desired={"auto_win":False,"skip_calls":False,"auto_discard":True,"auto_kita":False}
    assert handler.poll(o,desired)["reason"]=="assist_submitted"
    handler.read=lambda _:None
    now[0]=6
    assert handler.poll(o,desired)["reason"]=="waiting_for_assist_recovery" and o.halted
    assert len(m.clicks)==1


def test_optional_assist_can_be_prepared_again_next_hand(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    now=[1];o.clock=lambda:now[0];rgb=panel()
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    handler=AssistButtons();desired={"auto_win":True,"skip_calls":False,"auto_discard":False,"auto_kita":False}
    handler.poll(o,desired);now[0]=6;handler.poll(o,desired)
    assert "auto_win" in handler.unavailable
    r["state"]["round"]["ben"]+=1;now[0]=7
    assert handler.poll(o,desired)["reason"]=="assist_submitted" and len(m.clicks)==2


def test_own_turn_defers_optional_enabling_and_does_not_block_on_verified_off_pending(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    now=[1];o.clock=lambda:now[0];rgb=panel()
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    handler=AssistButtons();desired={"auto_win":True,"skip_calls":False,"auto_discard":False,"auto_kita":True}
    assert handler.poll(o,desired,prepare_optional=False) is None and not m.clicks
    now[0]=2
    assert handler.poll(o,desired)["reason"]=="assist_submitted" and len(m.clicks)==1
    now[0]=2.5
    assert handler.poll(o,desired,prepare_optional=False) is None
    assert handler.pending and handler.observed["auto_win"] is False and len(m.clicks)==1


def test_own_turn_still_disables_auto_kita_when_north_is_required(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    o.clock=lambda:1;rgb=panel();handler=AssistButtons()
    y=handler.profile["rows"]["auto_kita"]["y"]
    for yy in range(y-3,y+4):
        for x in range(57,64):rgb[(yy*1920+x)*3:(yy*1920+x)*3+3]=bytes(handler.profile["on"])
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    desired={"auto_win":True,"skip_calls":False,"auto_discard":False,"auto_kita":False}
    assert handler.poll(o,desired,prepare_optional=False)["reason"]=="assist_submitted"
    assert handler.pending[:2]==("auto_kita",False) and len(m.clicks)==1


def test_new_call_and_discard_assists_are_prepared_between_turns(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    o.clock=lambda:1;rgb=panel()
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    desired={"auto_win":True,"skip_calls":True,"auto_discard":True,"auto_kita":False}
    handler=AssistButtons()
    assert handler.poll(o,desired,prepare_optional=False) is None and not m.clicks


def test_opponent_step_does_not_starve_optional_ron_setup(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    o.clock=lambda:1;rgb=panel()
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    o.sleep=lambda _:r["state"].update(step=r["state"]["step"]+1)
    desired={"auto_win":True,"skip_calls":False,"auto_discard":False,"auto_kita":False}
    assert AssistButtons().poll(o,desired)["reason"]=="assist_submitted" and len(m.clicks)==1


def test_unconfirmed_old_hand_toggle_does_not_poison_next_hand(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    now=[1];o.clock=lambda:now[0];rgb=panel()
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    handler=AssistButtons();desired={"auto_win":True,"skip_calls":False,"auto_discard":False,"auto_kita":False}
    assert handler.poll(o,desired)["reason"]=="assist_submitted"
    r["state"]["round"]["ben"]+=1;now[0]=6
    assert handler.poll(o,desired)["reason"]=="assist_submitted" and not o.halted
    assert any(kind=="assist_retired" for kind,data in logs) and len(m.clicks)==2


def test_animation_wait_can_prepare_rk_but_never_enable_c_or_d(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    o.clock=lambda:1;rgb=panel()
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    handler=AssistButtons()
    desired={"auto_win":True,"auto_kita":True,"skip_calls":True,"auto_discard":True}
    handler.poll(o,desired,prepare_optional=False,prepare_automation=True)
    assert len(m.clicks)==1
    assert next(data["control"] for kind,data in logs if kind=="assist_attempt")=="auto_win"


def test_animation_wait_does_not_enable_c_or_d_when_rk_already_on(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    o.clock=lambda:1;handler=AssistButtons()
    states={"arrange":True,"auto_win":True,"auto_kita":True,"skip_calls":False,"auto_discard":False}
    def read(_):handler.layout="collapsed";return dict(states)
    monkeypatch.setattr(handler,"read",read)
    desired={"auto_win":True,"auto_kita":True,"skip_calls":True,"auto_discard":True}
    assert handler.poll(o,desired,prepare_optional=False,prepare_automation=True) is None
    assert not m.clicks


def test_unconfirmed_switch_recovers_without_click_when_states_become_known(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    o.clock=lambda:10;rgb=panel();handler=AssistButtons();handler.failed=True
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    assert handler.recover(o)
    assert not handler.failed and handler.pending is None
    assert handler.observed["skip_calls"] is False and not m.clicks
    assert logs[-1][0]=="assist_recovered"


def test_unknown_switch_recovery_keeps_polling_without_click(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    now=[10];o.clock=lambda:now[0];handler=AssistButtons();handler.failed=True
    monkeypatch.setattr(handler,"read",lambda _:None)
    assert not handler.recover(o) and handler.failed and not m.clicks
    assert not handler.recover(o)
    now[0]+=1
    rgb=panel();monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    monkeypatch.setattr(handler,"read",AssistButtons.read.__get__(handler))
    assert handler.recover(o) and not m.clicks


def test_recovery_rejects_changed_switches_or_hand(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="tracking",player_count=3)
    o.clock=lambda:10;handler=AssistButtons();handler.failed=True;rgb=panel()
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    o.sleep=lambda _:r["state"]["hand"].append("1z")
    assert not handler.recover(o) and handler.failed and not m.clicks


def test_recovery_can_resume_post_round_navigation_on_idle_wire(monkeypatch):
    o,r,m,logs=owner(monkeypatch);r["state"].update(status="match_ended",player_count=3)
    o.clock=lambda:10;handler=AssistButtons();handler.failed=True;rgb=panel()
    monkeypatch.setattr("games.mahjong_soul.live.runtime.assist_buttons.decode_frame",lambda _:rgb)
    o._current=lambda:(_ for _ in ()).throw(ValueError("Capture stale"))
    o._result_snapshot=lambda:r
    assert handler.recover(o) and not handler.failed and not m.clicks


def test_follower_clears_only_assist_halt_and_reconsiders_unattempted_board():
    from types import SimpleNamespace
    from agents.mahjong_soul.auto import AutoFollower
    from games.mahjong_soul.live.runtime.input import board_token
    report={"state":{"step":7},"game_connection":"synthetic","game_generation":1}
    token=board_token(report);seen={token};logs=[]
    follower=SimpleNamespace(assist_buttons=SimpleNamespace(failed=True,recover=lambda _:True),
        reader=SimpleNamespace(snapshot=lambda:report),
        controller=SimpleNamespace(was_attempted=lambda *a:False),
        halted="Assist switch outcome unconfirmed",candidate={"old":True},seen=seen,
        _record=lambda *a,**k:logs.append((a,k)))
    assert AutoFollower._recover_assist_input(follower)
    assert follower.halted is None and follower.candidate is None and token not in seen
    assert logs[-1][1]["confirmation"]=="assist_states_resynchronized"
