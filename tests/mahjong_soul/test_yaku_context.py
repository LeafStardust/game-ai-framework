from games.mahjong_soul.live.runtime.scoring_context import ScoringContext


def context(seat=1):
    c=ScoringContext(seat);r={"ju":0};discards=[[] for _ in range(4)];melds=[[] for _ in range(4)]
    c.observe("ActionNewRound",{},discards,melds,69,r,["1m"]*13)
    return c,r,discards,melds


def test_double_riichi_and_ippatsu_survive_draw_but_not_next_discard_or_call():
    c,r,d,m=context()
    c.observe("ActionDiscardTile",{"seat":1,"is_liqi":True},d,m,60,r,[])
    d[1].append({"tile":"1m"})
    assert c.snapshot()["double_riichi"] and c.snapshot()["ippatsu"]
    c.observe("ActionDealTile",{"seat":1,"left_tile_count":58},d,m,58,r,[])
    assert c.snapshot()["win"]["ippatsu"]
    c.observe("ActionDiscardTile",{"seat":1},d,m,58,r,[])
    assert not c.snapshot()["ippatsu"]
    c.observe("ActionChiPengGang",{"seat":2,"type":1},d,m,50,r,[])
    assert c.snapshot()["double_riichi"]  # Double Riichi stays a scored Yaku.


def test_call_cancels_ippatsu_and_replacement_draw_does_not_get_haitei():
    c,r,d,m=context();c.ippatsu[1]=True
    c.observe("ActionAnGangAddGang",{"seat":1,"type":3},d,m,1,r,[])
    assert not c.snapshot()["ippatsu"]
    c.observe("ActionDealTile",{"seat":1,"left_tile_count":0},d,m,1,r,[])
    assert c.snapshot()["win"]["rinshan"] and not c.snapshot()["win"]["haitei"]


def test_last_draw_last_discard_and_robbed_kan_have_explicit_context():
    c,r,d,m=context();d[1].append({"tile":"1m"})
    c.observe("ActionDealTile",{"seat":1,"left_tile_count":0},d,m,1,r,[])
    assert c.snapshot()["win"]["haitei"]
    c.observe("ActionDiscardTile",{"seat":2},d,m,0,r,[])
    assert c.snapshot()["win"]["houtei"]
    c.observe("ActionAnGangAddGang",{"seat":2,"type":2},d,m,0,r,[])
    assert c.snapshot()["win"]["chankan"] is True


def test_missing_history_does_not_guess_first_turn_or_event_yaku():
    c=ScoringContext(1)
    c.observe("ActionDealTile",{"seat":1,"left_tile_count":0},[[] for _ in range(4)],[[] for _ in range(4)],1,{"ju":0},[])
    assert not c.snapshot()["history_complete"] and c.snapshot()["win"]=={}


def test_tenhou_and_chiihou_require_uninterrupted_first_turn():
    c=ScoringContext(0);d=[[] for _ in range(4)];m=[[] for _ in range(4)]
    c.observe("ActionNewRound",{},d,m,69,{"ju":0},["1m"]*14)
    assert c.snapshot()["win"]["tenhou"]
    c,r,d,m=context();c.observe("ActionDealTile",{"seat":1},d,m,69,r,[])
    assert c.snapshot()["win"]["chiihou"]
    m[0].append({"type":1})
    c.observe("ActionDealTile",{"seat":1},d,m,68,r,[])
    assert not c.snapshot()["win"]["chiihou"]


def test_robbed_kan_preserves_ippatsu_but_successful_kan_cancels_it():
    c,r,d,m=context();c.ippatsu[1]=True
    c.observe("ActionAnGangAddGang",{"seat":2,"type":2},d,m,10,r,[])
    assert c.snapshot()["win"]["chankan"] and c.snapshot()["win"]["ippatsu"]
    assert not c.snapshot()["ippatsu"]


def test_discard_after_last_replacement_draw_can_still_be_houtei():
    c,r,d,m=context()
    c.observe("ActionAnGangAddGang",{"seat":2,"type":3},d,m,1,r,[])
    c.observe("ActionDealTile",{"seat":2,"left_tile_count":0},d,m,1,r,[])
    c.observe("ActionDiscardTile",{"seat":2},d,m,0,r,[])
    assert c.snapshot()["win"]["houtei"]


def test_first_discard_double_riichi_opportunity_is_not_assumed_after_call_or_reconnect():
    c,r,d,m=context();assert c.snapshot()["double_riichi_available"]
    c.observe("ActionDiscardTile",{"seat":1},d,m,60,r,[])
    assert not c.snapshot()["double_riichi_available"]
    c,r,d,m=context();c.observe("ActionChiPengGang",{"seat":2,"type":1},d,m,60,r,[])
    assert not c.snapshot()["double_riichi_available"]
    assert not ScoringContext(1).snapshot()["double_riichi_available"]
