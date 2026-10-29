import pytest
from games.mahjong_soul.live.runtime.ranked_end import insufficient_copper,final_ranked_screen
from tests.mahjong_soul.test_result_buttons import word
from tests.mahjong_soul.test_ranked_requeue import setup


def end_words():return [word("Match Results",x=700,y=200),word("Back",x=800,y=950)]


@pytest.mark.parametrize("caption",["Insufficient Copper","Not enough Copper","Insufficient coins","Not enough coins","You don't have enough Copper","Insufficient amount of Copper"])
def test_explicit_currency_errors_are_recognized(caption):
    assert insufficient_copper([word(caption,x=700,y=400)]) is not None


def test_split_currency_message_is_recognized_without_inferring_from_missing_button():
    assert insufficient_copper([word("Not",x=600,y=400),word("enough",x=730,y=400),word("Copper",x=860,y=400)])
    assert insufficient_copper([word("Copper",x=700,y=400)]) is None
    assert insufficient_copper([word("You have enough Copper",x=700,y=400)]) is None
    assert insufficient_copper([word("Insufficient points",x=700,y=400)]) is None


def test_final_screen_does_not_require_one_more_game():
    assert final_ranked_screen(end_words()) is not None
    assert final_ranked_screen([word("Match Results",x=700,y=70),word("Back",x=800,y=950)]) is not None
    assert final_ranked_screen([word("Han",y=200),word("Confirm")]) is None
    assert final_ranked_screen([word("Back")]) is None
    assert final_ranked_screen([word("Match Results",y=200)]) is None


def test_ranked_reward_summary_with_exit_is_independent_final_evidence():
    w=[word("Rank Points",x=700,y=300),word("Copper",x=700,y=400),word("Return to Lobby",x=800,y=950)]
    assert final_ranked_screen(w)


def test_game_limit_stops_on_verified_final_results_without_more_button(monkeypatch):
    o,r,m,logs,h,now=setup(monkeypatch,1)
    h.ocr=lambda _:end_words()
    assert h.poll(o)["reason"]=="game_limit_reached" and not m.clicks


@pytest.mark.parametrize("limit",[3,None])
def test_insufficient_copper_stops_cleanly_before_requested_count(monkeypatch,limit):
    o,r,m,logs,h,now=setup(monkeypatch,limit)
    h.ocr=lambda _:[word("Insufficient Copper",x=700,y=400),word("OK",x=800,y=700)]
    event=h.poll(o)
    assert event=={"kind":"finished","reason":"insufficient_copper","completed":1,"limit":limit}
    assert not m.clicks


def test_missing_button_alone_is_not_misreported_as_insufficient_copper(monkeypatch):
    o,r,m,logs,h,now=setup(monkeypatch,3)
    h.ocr=lambda _:end_words()
    assert h.poll(o)["reason"]=="waiting_for_ranked_continuation_button"
    now[0]=10
    assert h.poll(o)["reason"]=="ranked_continuation_unavailable"
    assert not m.clicks


def test_one_more_button_appearing_during_grace_period_can_requeue(monkeypatch):
    from tests.mahjong_soul.test_ranked_requeue import words
    o,r,m,logs,h,now=setup(monkeypatch,3)
    h.ocr=lambda _:end_words()
    assert h.poll(o)["reason"]=="waiting_for_ranked_continuation_button"
    h.ocr=lambda _:words();now[0]=2
    assert h.poll(o)["reason"]=="ranked_requeue_submitted" and len(m.clicks)==1


def test_clean_currency_stop_remains_terminal_without_reaching_game_limit(monkeypatch):
    from tests.mahjong_soul.test_auto import setup as auto_setup
    from agents.mahjong_soul.game_budget import GameBudget
    f,r,p,e,m=auto_setup(monkeypatch);f.game_budget=GameBudget(3)
    f.game_budget.completed.add((r["game_connection"],r.get("game_generation",0)))
    event=f._stop_ranked_continuation(r,"insufficient_copper")
    assert event["kind"]=="finished" and not f.enabled and not f.game_budget.done
    assert f.poll()==event and f._game_limit()==event and not m.clicks


def test_still_visible_requeue_control_after_bounded_retries_stops_cleanly(monkeypatch):
    o,r,m,logs,h,now=setup(monkeypatch,3)
    assert h.poll(o)["reason"]=="ranked_requeue_submitted"
    now[0]=5;assert h.poll(o)["reason"]=="ranked_requeue_submitted"
    now[0]=14;assert h.poll(o)["reason"]=="ranked_requeue_unconfirmed"
    assert len(m.clicks)==2


def test_real_matching_screen_is_not_stopped_as_unavailable(monkeypatch):
    o,r,m,logs,h,now=setup(monkeypatch,3)
    h.poll(o)
    h.ocr=lambda _:end_words()+[word("Matching",x=800,y=400),word("Cancel",x=800,y=700)]
    now[0]=30
    assert h.poll(o)["reason"]=="waiting_for_ranked_match" and len(m.clicks)==1
