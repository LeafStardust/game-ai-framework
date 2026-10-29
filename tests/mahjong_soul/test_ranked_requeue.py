import pytest
from agents.mahjong_soul.game_budget import GameBudget
from games.mahjong_soul.live.runtime.result_buttons import ResultButtons
from games.mahjong_soul.live.runtime.ranked_requeue import one_more_game
from tests.mahjong_soul.test_result_buttons import owner,word
from tests.mahjong_soul.test_ranked_access import auth
from games.mahjong_soul.live.runtime.lobby import detect_lobby


def words():return [word("Results",y=200),word("One",x=1050),word("More",x=1180),word("Game",x=1310)]


def setup(monkeypatch,limit=3,completed=1):
    o,r,m,logs=owner(monkeypatch);o.require_ai=True;o.allow_ranked=True
    monkeypatch.setattr("games.mahjong_soul.live.runtime.ranked_requeue.decode_frame",lambda _:bytes(1920*1080*3))
    r["state"].update(status="match_ended",lobby=detect_lobby(auth()))
    key=(r["game_connection"],r.get("game_generation",0));o.ranked_games={key}
    b=GameBudget(limit);b.active.add(key);b.completed.add(key)
    for i in range(completed-1):b.completed.add((f"synthetic-{i}",1))
    o.game_budget=b
    now=[1];o.clock=lambda:now[0]
    h=ResultButtons(lambda _:words())
    return o,r,m,logs,h,now


@pytest.mark.parametrize("completed",[1,2])
def test_three_game_command_requeues_after_first_and_second(monkeypatch,completed):
    o,r,m,logs,h,now=setup(monkeypatch,3,completed)
    assert h.poll(o)["reason"]=="ranked_requeue_submitted"
    assert len(m.clicks)==1 and h.pending=="one_more_game"
    event=next(data for kind,data in logs if kind=="ranked_requeue_attempt")
    assert event["completed"]==completed and event["limit"]==3


@pytest.mark.parametrize("limit,completed",[(1,1),(3,3)])
def test_never_requeues_after_command_limit(monkeypatch,limit,completed):
    o,r,m,logs,h,now=setup(monkeypatch,limit,completed)
    assert h.poll(o) is None and not m.clicks


def test_unlimited_command_can_requeue(monkeypatch):
    o,r,m,logs,h,now=setup(monkeypatch,None)
    assert h.poll(o)["reason"]=="ranked_requeue_submitted" and len(m.clicks)==1


@pytest.mark.parametrize("case",["historical","round_only","unverified","unknown_lobby"])
def test_requires_this_runs_completed_verified_ranked_match(monkeypatch,case):
    o,r,m,logs,h,now=setup(monkeypatch)
    if case=="historical":o.game_budget.completed.clear()
    if case=="round_only":r["state"]["status"]="round_ended"
    if case=="unverified":o.ranked_games.clear()
    if case=="unknown_lobby":r["state"]["lobby"]["ranked"]=False
    assert h.poll(o) is None and not m.clicks


@pytest.mark.parametrize("caption",["One More Game","One more game!"])
def test_complete_or_split_caption_requires_result_context(caption):
    assert one_more_game(words())==(1240,965)
    assert one_more_game([word("Result",y=200),word(caption,x=1100)])==(1160,965)
    assert one_more_game([word(caption,x=1100)]) is None
    assert one_more_game([word("Result",y=200),word("Game",x=1100)]) is None


def test_ambiguous_duplicate_buttons_are_rejected():
    assert one_more_game(words()+[word("One More Game",x=600,y=850)]) is None


@pytest.mark.parametrize("change",["board","budget","pixels"])
def test_rechecks_board_budget_and_pixels_before_queue_input(monkeypatch,change):
    o,r,m,logs,h,now=setup(monkeypatch)
    if change=="board":o.sleep=lambda _:r["state"].update(step=999)
    if change=="budget":o.sleep=lambda _:o.game_budget.completed.update({("extra1",1),("extra2",1)})
    if change=="pixels":
        images=iter([b"first",b"moved"]);o._frame=lambda *a:next(images)
        monkeypatch.setattr("games.mahjong_soul.live.runtime.ranked_requeue.decode_frame",lambda p:bytes([0 if p==b"first" else 255])*(1920*1080*3))
    assert h.poll(o)["reason"]=="waiting_for_stable_ranked_results" and not m.clicks


def test_requeue_retry_requires_same_label_and_is_delayed_and_bounded(monkeypatch):
    o,r,m,logs,h,now=setup(monkeypatch)
    assert h.poll(o)["reason"]=="ranked_requeue_submitted"
    now[0]=2;assert h.poll(o)["reason"]=="waiting_for_ranked_match" and len(m.clicks)==1
    now[0]=5;assert h.poll(o)["reason"]=="ranked_requeue_submitted" and len(m.clicks)==2
    now[0]=9;assert h.poll(o)["reason"]=="waiting_for_ranked_match" and len(m.clicks)==2


def test_new_match_confirms_queue_without_counting_another_completion(monkeypatch):
    o,r,m,logs,h,now=setup(monkeypatch)
    h.poll(o);r["state"]["status"]="waiting_for_round";r["game_generation"]+=1
    assert h.poll(o) is None and h.pending is None and len(o.game_budget.completed)==1
    assert logs[-1]==("result_button_confirmed",{"button":"one_more_game","confirmation":"game_state_advanced"})


def test_cancel_overlay_is_not_a_one_more_game_control():
    assert one_more_game(words()+[word("Cancel",x=700,y=800)]) is None


def test_queue_wait_never_clicks_other_confirm_or_cancel_controls(monkeypatch):
    o,r,m,logs,h,now=setup(monkeypatch)
    assert h.poll(o)["reason"]=="ranked_requeue_submitted"
    h.ocr=lambda _:[word("Results",y=200),word("Confirm"),word("Cancel",x=700,y=800)]
    now[0]=5
    assert h.poll(o)["reason"]=="waiting_for_ranked_match" and len(m.clicks)==1


def test_command_three_runs_exactly_two_requeues_then_finishes(monkeypatch):
    o,r,m,logs,h,now=setup(monkeypatch,3)
    o._game_limit=lambda:({"kind":"finished","reason":"game_limit_reached","completed":len(o.game_budget.completed),"limit":3}
                           if o.game_budget.done else None)
    assert h.poll(o)["reason"]=="ranked_requeue_submitted"
    for generation in (2,3):
        r["game_generation"]=generation;r["state"]["status"]="tracking"
        o.ranked_games.add((r["game_connection"],generation))
        o.game_budget.observe(r);h.poll(o)
        r["state"]["status"]="match_ended";o.game_budget.observe(r)
        event=h.poll(o)
        if generation==2:assert event["reason"]=="ranked_requeue_submitted"
        else:assert event["kind"]=="finished" and event["completed"]==3
    assert len(m.clicks)==2 and len(o.game_budget.completed)==3
