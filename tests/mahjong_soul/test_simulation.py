import json
import pytest
engine=pytest.importorskip("riichienv",reason="Optional offline simulator is not installed")
from agents.mahjong_soul.simulation import tile,request,run,Agent


def test_exact_tile_mapping_and_public_observation():
    assert [tile(t) for t in (0,32,52,53,88,108,132)]==["1m","9m","0p","5p","0s","1z","7z"]
    env=engine.RiichiEnv(game_mode="3p-red-single",seed=3);obs=env.reset()[0]
    req,bindings=request(obs);board=req["observation"]["board"]
    assert all(not h for i,h in enumerate(obs.hands) if i!=obs.player_id)
    assert len(board["self"]["hand"])==14
    assert set(board["self"])-{"hand","opening_hand","drawn_tile","furiten","scoring_context"}==set()
    assert board["wall_remaining"]==54
    assert len(bindings)==len(req["actions"])
    assert all(a in req["actions"] for a,native in bindings)
    assert all(v<=4 for v in board["visible_tile_counts"].values())


def test_seeded_complete_hand_is_reproducible():
    a=run(3,0,"efficiency",mode="3p-red-single");b=run(3,0,"efficiency",mode="3p-red-single")
    assert a["log"]==b["log"] and a["scores"]==b["scores"] and a["initial_deal_digest"]==b["initial_deal_digest"]
    assert a["hands"]==1 and sum(a["scores"])==105000


@pytest.mark.parametrize("tsumo",[False,True])
def test_engine_and_live_scoring_agree_on_closed_sanma_hand(tsumo):
    from agents.mahjong_soul.scoring import score_hand,allocate
    hand=["1p","2p","3p","4p","5p","6p","2s","3s","4s","6s","7s","8s","5z"]
    ids=allocate([hand,["5z"]]);conditions=engine.Conditions(riichi=True,tsumo=tsumo,player_wind=1,round_wind=0,is_sanma=True,num_players=3)
    actual=engine.HandEvaluator3P(ids[0]).calc(ids[1][0],conditions=conditions)
    expected=score_hand(hand,"5z",riichi=True,tsumo=tsumo,player_count=3,seat_wind=1)
    assert actual.is_win and expected["legal"] and (actual.han,actual.fu)==(expected["han"],expected["fu"])
    points=actual.tsumo_agari_oya+actual.tsumo_agari_ko if tsumo else actual.ron_agari
    assert points==expected["points"]


def test_push_variant_does_not_modify_live_playbooks():
    from games.mahjong_soul.playbook.sanma.east_speed import three_player_east_speed_playbook
    push=Agent("east_speed_push");normal=Agent("east_speed")
    assert push.policy.registry.get(3,"atk","east").strategy["defense"]["always_push"]
    assert not normal.policy.registry.get(3,"atk","east").strategy["defense"]["always_push"]
    assert not three_player_east_speed_playbook().strategy["defense"]["always_push"]


def test_unknown_candidate_is_not_silently_baseline():
    with pytest.raises(ValueError,match="Unknown simulation candidate"):
        Agent("typo")


def test_wait_quality_variant_is_isolated_from_live_settings():
    candidate=Agent("east_speed_lookahead");normal=Agent("east_speed")
    assert candidate.policy.registry.get(3,"atk","east").thresholds_for("D1")["next_wait_tiebreak"]
    assert not normal.policy.registry.get(3,"atk","east").thresholds_for("D1").get("next_wait_tiebreak")


def test_two_draw_candidate_is_not_enabled_in_live_policy():
    candidate=Agent("east_speed_two_draw");normal=Agent("east_speed")
    assert candidate.policy.registry.get(3,"atk","east").thresholds_for("D1")["two_draw_progress"]
    assert not normal.policy.registry.get(3,"atk","east").thresholds_for("D1").get("two_draw_progress")


def test_earlier_hand_candidate_is_isolated_from_live_policy():
    candidate=Agent("east_speed_development");normal=Agent("east_speed")
    assert candidate.policy.registry.get(3,"atk","east").thresholds_for("D1")["early_development"]
    assert not normal.policy.registry.get(3,"atk","east").thresholds_for("D1").get("early_development")


def test_old_partial_yaku_gate_is_offline_only():
    old=Agent("east_speed_partial_yaku");normal=Agent("east_speed")
    assert not old.policy.registry.get(3,"atk","east").strategy["defense"]["allow_scored_ready_yaku"]
    assert normal.policy.registry.get(3,"atk","east").strategy["defense"]["allow_scored_ready_yaku"]


def test_ready_push_candidate_does_not_enable_live_risk_override():
    candidate=Agent("east_speed_ready_push");normal=Agent("east_speed")
    settings=candidate.policy.registry.get(3,"atk","east").strategy["defense"]
    assert settings["ready_push_max_danger"]==90 and settings["ready_push_min_ukeire"]==3
    assert "ready_push_max_danger" not in normal.policy.registry.get(3,"atk","east").strategy["defense"]


@pytest.mark.parametrize("seat",[0,1,2])
def test_mixed_opponents_rotate_relative_to_candidate_seat(seat):
    from agents.mahjong_soul.simulation import seat_policies
    names=seat_policies(seat,"east_speed_ready_push","mixed")
    assert names[seat]=="east_speed_ready_push"
    assert names[(seat+1)%3]=="east_speed"
    assert names[(seat+2)%3]=="east_speed_push"


@pytest.mark.parametrize("profile",["callers","aggressive","mixed"])
def test_call_capable_opponents_complete_legal_reproducible_hand(profile):
    a=run(3,0,"east_speed",mode="3p-red-single",opponents=profile)
    b=run(3,0,"east_speed",mode="3p-red-single",opponents=profile)
    assert a["log"]==b["log"] and a["hands"]==1
    assert a["opponent_profile"]==profile
    assert set(a["opponents_by_seat"])=={"1","2"}
    assert all(counts for counts in a["action_counts"])


def test_invalid_opponent_setup_is_not_silently_efficiency():
    from agents.mahjong_soul.simulation import seat_policies
    with pytest.raises(ValueError,match="Unknown opponent profile"):
        seat_policies(0,"east_speed","typo")
    with pytest.raises(ValueError,match="Seat must"):
        seat_policies(3,"east_speed","callers")


def test_duplicate_physical_discards_have_one_intent_and_keep_red_five():
    env=engine.RiichiEnv(game_mode="3p-red-single",seed=7);obs=env.reset()[0]
    native=obs.legal_actions();req,bindings=request(obs)
    discards=[a for a in req["actions"] if a["kind"]=="discard"]
    assert sum(int(a.action_type)==0 for a in native)>len(discards)
    assert {a["tile"] for a in discards}=={tile(t) for t in obs.hand}
    assert len(discards)==len({a["tile"] for a in discards})
    assert {"0s","5s"}<={a["tile"] for a in discards}
    for intent,action in bindings:
        if intent["kind"]=="discard":
            first=next(a for a in native if int(a.action_type)==0 and tile(a.tile)==intent["tile"])
            assert action.tile==first.tile
    codes=req["observation"]["board"]["available_operations"]["operation_list"]
    assert len(codes)==len({c["type"] for c in codes})
    action=next(a for intent,a in bindings if intent=={"kind":"discard","tile":"5s"})
    env.step({0:action})  # The retained exact physical binding is engine-legal.


def test_duplicate_riichi_discard_keeps_one_offer_and_two_stage_binding():
    from agents.mahjong_soul.simulation import events
    env=engine.RiichiEnv(game_mode="3p-red-single",seed=0);observations=env.reset()
    agents={p:Agent("efficiency") for p in range(3)}
    for _ in range(500):
        for pid,obs in observations.items():
            if not any(int(a.action_type)==5 for a in obs.legal_actions()):continue
            assert [tile(t) for t in obs.hand].count("9p")==2
            req,bindings=request(obs,agents[pid].history+events(obs))
            reaches=[a for a in req["actions"] if a["kind"]=="riichi"]
            assert reaches==[{"kind":"riichi","tile":"9p"}]
            reach=agents[pid].act(obs)
            assert int(reach.action_type)==5
            following=env.step({pid:reach})
            discard=agents[pid].act(following[pid])
            assert int(discard.action_type)==0 and tile(discard.tile)=="9p"
            env.step({pid:discard})
            return
        if env.done():break
        observations=env.step({pid:agents[pid].act(obs) for pid,obs in observations.items()})
    pytest.fail("Seeded regression did not reach the expected Riichi offer")


def test_call_width_candidate_is_offline_and_isolated():
    candidate=Agent("east_speed_call_width");normal=Agent("east_speed")
    assert candidate.policy.registry.get(3,"atk","east").strategy["calls"]["unsecured_opening_min_ukeire"]==8
    assert not normal.policy.registry.get(3,"atk","east").strategy["calls"].get("unsecured_opening_min_ukeire")


def test_completion_candidate_is_offline_and_isolated():
    candidate=Agent("east_speed_completion");normal=Agent("east_speed")
    assert candidate.policy.registry.get(3,"atk","east").strategy["calls"]["completion_opening_guard"] is True
    assert not normal.policy.registry.get(3,"atk","east").strategy["calls"].get("completion_opening_guard")
    assert not candidate.policy.registry.get(4,"atk","east").strategy["calls"].get("completion_opening_guard")
    assert not candidate.policy.registry.get(4,"atk","south").strategy["calls"].get("completion_opening_guard")


def test_discard_completion_is_enabled_only_for_three_player_east():
    candidate=Agent("east_speed_discard_completion");normal=Agent("east_speed")
    assert candidate.policy.registry.get(3,"atk","east").thresholds_for("D1")["discard_completion"] is True
    assert normal.policy.registry.get(3,"atk","east").thresholds_for("D1")["discard_completion"] is False
    from agents.mahjong_soul.policy import make_policy
    production=make_policy("playbook","atk").registry.get(3,"atk","east")
    assert production.version=="0.7" and production.thresholds_for("D1")["discard_completion"] is True
    assert not candidate.policy.registry.get(4,"atk","east").thresholds_for("D1").get("discard_completion")
    assert not candidate.policy.registry.get(4,"atk","south").thresholds_for("D1").get("discard_completion")
