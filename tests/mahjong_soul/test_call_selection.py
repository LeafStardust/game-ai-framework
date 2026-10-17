from copy import deepcopy
from dataclasses import replace
import pytest

from games.mahjong_soul.live.runtime.call_selection import plan_call, plan_call_choice, CallMenuPlan
from games.mahjong_soul.live.runtime.choice_vision import bind_faces, face_boxes
from games.mahjong_soul.live.runtime.controller import InputController
from games.mahjong_soul.live.runtime.input import board_token
from tests.mahjong_soul.test_calls import multi_chi_offer, offer as pon_offer
from tests.mahjong_soul.test_kan_input import offer as closed_offer, open_offer, added_offer
from tests.mahjong_soul.test_input import Mouse


def profile(report):
    return {"version":1,"verified":True,"stage":"call_offer","client_size":[1920,1080],
            "operation_types":[o["type"] for o in report["state"]["operations"]["operation_list"]],
            "chi":[.53,.77],"pon":[.53,.77],"kan":[.53,.77]}


def multi(kind):
    if kind=="chi":
        report,_,choices=multi_chi_offer()
    elif kind=="pon":
        report,_=pon_offer();report["state"]["hand"]=["0p","5p","5p"]
        choices=["0p|5p","5p|5p"]
    elif kind=="closed_kan":
        report,_=closed_offer();report["state"]["hand"]=["0p","5p","5p","5p"]+["1m"]*4
        choices=["0p|5p|5p|5p","1m|1m|1m|1m"]
    else:
        report,_=added_offer()
        report["state"]["hand"].append("1m")
        report["state"]["melds"][0].append({"type":1,"tiles":["1m"]*3,"froms":[0,0,2]})
        choices=["5p|5p|5p|0p","1m|1m|1m|1m"]
    code={"chi":2,"pon":3,"closed_kan":4,"added_kan":6}[kind]
    next(o for o in report["state"]["operations"]["operation_list"] if o["type"]==code)["combination"]=choices
    return report,choices


@pytest.mark.parametrize("kind",["chi","pon","closed_kan","added_kan"])
def test_reordered_choice_panel_selects_policy_contribution_as_one_action(kind):
    report,choices=multi(kind);original=deepcopy(report)
    action={"kind":kind,"combination":choices[0]}
    menu=plan_call(report,profile(report),action,now=10)
    assert isinstance(menu,CallMenuPlan)
    assert menu.token==board_token(report)
    panel=dict(profile(report),stage="call_choices",combinations=list(reversed(choices)),choice_points=[[.4+i*.1,.7] for i in range(len(choices))])
    choice=plan_call_choice(report,panel,action,now=11)
    assert choice.x==.4+(len(choices)-1)*.1 and choice.token==menu.token
    mouse=Mouse();controller=InputController(mouse)
    controller.submit(menu,report,enabled=True,now=11)
    controller.select_call_combination(choice,report,enabled=True,now=12)
    assert len(mouse.clicks)==2
    assert controller.snapshot()["attempted_steps"]==1
    assert controller.snapshot()["pending"]["token"]==board_token(report)
    with pytest.raises(ValueError):controller.select_call_combination(choice,report,enabled=True,now=12)
    assert report==original


@pytest.mark.parametrize("kind,factory",[("closed_kan",closed_offer),("open_kan",open_offer),("added_kan",added_offer)])
def test_all_kan_variants_use_canonical_confirmation(kind,factory):
    report,_=factory();code={"closed_kan":4,"open_kan":5,"added_kan":6}[kind]
    combo=next(o["combination"][0] for o in report["state"]["operations"]["operation_list"] if o["type"]==code)
    plan=plan_call(report,profile(report),{"kind":kind,"combination":combo},now=10)
    mouse=Mouse();controller=InputController(mouse)
    controller.submit(plan,report,enabled=True,now=11)
    if kind=="open_kan":
        event={"name":"ActionChiPengGang","step":1,"source":"live",
               "data":{"seat":0,"type":2,"tiles":["0p","5p","5p","5p"],"froms":[0,0,0,3]}}
    else:
        event={"name":"ActionAnGangAddGang","step":1,"source":"live",
               "data":{"seat":0,"type":3 if kind=="closed_kan" else 2,"tiles":"5p" if kind=="closed_kan" else "0p"}}
    assert controller.observe("game",event,now=12)
    assert controller.snapshot()["status"]=="idle"


@pytest.mark.parametrize("problem",["different_choice","new_board","partial_delivery","stale_panel"])
def test_call_menu_cannot_select_wrong_choice_or_retry_uncertain_input(problem):
    report,choices=multi("pon");action={"kind":"pon","combination":choices[0]}
    menu=plan_call(report,profile(report),action,now=10)
    class Failure(Mouse):
        def click(self,*args):
            super().click(*args)
            if len(self.clicks)==2:raise OSError("partial delivery")
    mouse=Failure() if problem=="partial_delivery" else Mouse();controller=InputController(mouse)
    controller.submit(menu,report,enabled=True,now=11)
    panel=dict(profile(report),stage="call_choices",combinations=choices,choice_points=[[.4,.7],[.6,.7]])
    if problem=="stale_panel":panel["combinations"]=[choices[0],choices[0]]
    if problem=="different_choice":action["combination"]=choices[1]
    if problem=="stale_panel":
        with pytest.raises(ValueError):plan_call_choice(report,panel,action,now=11)
        assert len(mouse.clicks)==1
        return
    choice=plan_call_choice(report,panel,action,now=11)
    if problem=="new_board":report["state"]["step"]+=1
    with pytest.raises((ValueError,OSError)):controller.select_call_combination(choice,report,enabled=True,now=12)
    assert len(mouse.clicks)==(2 if problem=="partial_delivery" else 1)
    if problem=="partial_delivery":assert controller.snapshot()["status"]=="blocked"


def test_visual_binding_uses_screen_order_and_exact_red_identity():
    report,choices=multi("pon");action={"kind":"pon","combination":choices[0]}
    faces=[((500,680,60,100),"5p",bytes(648)),((562,680,60,100),"5p",bytes(648)),
           ((800,680,60,100),"0p",bytes(648)),((862,680,60,100),"5p",bytes(648))]
    panel,_=bind_faces(faces,report,action)
    assert panel["combinations"]==list(reversed(choices))
    assert plan_call_choice(report,panel,action,now=10).x>.4
    faces[2]=(faces[2][0],"5p",faces[2][2])
    with pytest.raises(ValueError,match="whole call choice"):bind_faces(faces,report,action)


def test_face_detection_excludes_standing_hand_and_non_tile_regions():
    rgb=bytearray(1920*1080*3)
    for x,y,w,h in [(500,680,60,100),(562,680,60,100),(900,950,90,120),(1100,700,100,50)]:
        for row in range(y,y+h):
            rgb[(row*1920+x)*3:(row*1920+x+w)*3]=bytes([220])*(w*3)
    assert face_boxes(rgb)==[(500,680,60,100),(562,680,60,100)]


@pytest.mark.parametrize("visible",[False,True])
def test_kan_label_presence_requires_outlined_text_at_reviewed_point(monkeypatch,visible):
    from games.mahjong_soul.live.runtime.visual import TileVision
    import games.mahjong_soul.live.runtime.visual as visual
    rgb=bytearray([110,145,130])*(1920*1080)
    if visible:
        for x in range(950,1090,20):
            for y in range(788,835):
                for px in range(x,x+12):
                    i=(y*1920+px)*3
                    rgb[i:i+3]=bytes([220,210,185]) if x+3<=px<x+9 and 791<=y<832 else bytes([40,40,40])
    monkeypatch.setattr(visual,"decode_frame",lambda _:rgb)
    vision=TileVision()
    if visible:assert vision.button(b"frame","kan",point=(1020,835))[:2]==(1020,835)
    else:
        with pytest.raises(ValueError,match="not visible"):vision.button(b"frame","kan",point=(1020,835))
