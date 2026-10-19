from copy import deepcopy
from agents.mahjong_soul.yakuman import yakuman_targets
from agents.mahjong_soul.attack_routes import project_attack,route_progress
from tests.mahjong_soul.test_attack_v2 import board,call_report,choose
from tests.mahjong_soul.test_efficiency import tiles


def targets(opening,current=None):
    b=board(current or opening);b["self"]["opening_hand"]=tiles(opening)
    return b,{t["target_route"]:t for t in yakuman_targets(b,b["self"]["hand"])}


def test_kokushi_gate_counts_useful_distinct_tiles_and_one_pair_only():
    _,qualified=targets("19m19p19s1234z234m")
    assert qualified["yakuman_kokushi"]["opening_matches"]==10
    _,below=targets("19m19p19s123z2345m")
    assert "yakuman_kokushi" not in below
    _,duplicates=targets("111999m111p2345s")
    assert "yakuman_kokushi" not in duplicates


def test_later_natural_hand_can_enable_yakuman_without_opening_history():
    b,t=targets("123456m234p567s1z","19m19p19s1234567z")
    assert "yakuman_kokushi" in t
    assert t["yakuman_kokushi"]["qualification"]=="current"
    b["self"].pop("opening_hand")
    assert yakuman_targets(b,b["self"]["hand"])


def test_qualified_kokushi_progress_does_not_credit_unrelated_tiles():
    b,t=targets("19m19p19s1234z234m")
    distance,improving=route_progress(b,b["self"]["hand"],t["yakuman_kokushi"])
    assert distance==3
    assert all(x["tile"] in {"1m","9m","1p","9p","1s","9s","1z","2z","3z","4z","5z","6z","7z"} for x in improving)


def test_nine_gates_gate_uses_required_multiplicities_not_just_suit_count():
    _,yes=targets("1112345678m234p")
    assert yes["yakuman_nine_gates"]["opening_matches"]==10
    _,no=targets("2222333344m567p")
    assert "yakuman_nine_gates" not in no


def test_qualified_honor_target_cannot_keep_an_off_suit_fixed_meld():
    b,t=targets("1112223334z123m")
    assert "yakuman_all_honors" in t
    own=next(p for p in b["players"] if p["is_self"])
    own["melds"]=[{"type":0,"tiles":tiles("123m")}]
    assert not yakuman_targets(b,b["self"]["hand"])


def test_cheap_call_does_not_override_high_value_priority_even_under_riichi():
    r=call_report("55z123m456p78s22p9m","5z","5z|5z")
    assert choose(r)[0]["kind"]=="skip"
    r["state"]["riichi"][1]="accepted"
    assert choose(r)[0]["kind"]=="skip"


def test_opening_hand_survives_mutation_and_is_copied_to_observation():
    from games.mahjong_soul.live.runtime.state import GameState
    from games.mahjong_soul.live.runtime.observation import observation_from_snapshot
    state=GameState(0);initial=tiles("19m19p19s1234z234m")
    state.apply({"name":"ActionNewRound","step":0,"data":{"tiles":initial,"scores":[25000]*4}})
    state.hand.pop()
    assert state.snapshot()["opening_hand"]==initial
    report={"state":state.snapshot(),"state_ready":True,"game_connection":"test","connection_open":True}
    observed=observation_from_snapshot(report)["board"]["self"]["opening_hand"]
    assert observed==initial
    observed.clear()
    assert state.opening_hand==initial


def test_qualified_opening_drives_actual_discard_policy():
    from tests.mahjong_soul.test_attack_v2 import report
    r=report("19m19p19s1234z2345m")
    r["state"]["opening_hand"]=tiles("19m19p19s1234z234m")
    action,analysis=choose(r)
    assert analysis["target_route"]=="yakuman_kokushi"
    assert action["kind"]=="discard" and action["tile"] in {"2m","3m","4m","5m"}


def test_next_round_cannot_reuse_previous_yakuman_opening():
    from games.mahjong_soul.live.runtime.state import GameState
    state=GameState(0)
    for hand in ("19m19p19s1234z234m","123456m234p567s1z"):
        state.apply({"name":"ActionNewRound","step":0,"data":{"tiles":tiles(hand),"scores":[25000]*4}})
        assert state.snapshot()["opening_hand"]==tiles(hand)


def test_late_threshold_is_rejected_when_wall_cannot_supply_required_draws():
    b,_=targets("123456m234p567s1z","19m19p19s1234z234m")
    b["wall_remaining"]=8
    assert not yakuman_targets(b,b["self"]["hand"])


def test_dead_required_kokushi_tile_disables_pursuit():
    b,_=targets("19m19p19s1234z234m")
    b["visible_tile_counts"]["7z"]=4
    assert not yakuman_targets(b,b["self"]["hand"])


def test_below_threshold_never_advertises_yakuman_value():
    b,_=targets("123456m234p567s1z")
    assert not any(t["target_route"].startswith("yakuman_") for t in project_attack(b,b["self"]["hand"],all_targets=True))


def test_decision_record_includes_competing_discard_outcomes():
    from tests.mahjong_soul.test_attack_v2 import report
    action,analysis=choose(report("123m456p789s11z99p2z"))
    assert analysis["discard_evaluations"]
    assert any(o["action"]["tile"]==action["tile"] for o in analysis["discard_evaluations"])
