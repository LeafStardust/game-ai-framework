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
