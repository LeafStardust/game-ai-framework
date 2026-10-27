import pytest
from agents.mahjong_soul.attack_policy import offensive
from agents.mahjong_soul.attack_defense import riichi_genbutsu
from games.mahjong_soul.playbook.model import default_mahjong_playbooks


def setup():
    board={"self":{"drawn_tile":"5p","hand":["2p","5p"]},"wall_remaining":30,
           "players":[{"seat":0,"is_self":True,"riichi":"none","melds":[],"discards":[]},
                      {"seat":1,"is_self":False,"riichi":"accepted","melds":[],"discards":[{"tile":"2p"}]},
                      {"seat":2,"is_self":False,"riichi":"none","melds":[],"discards":[]}]}
    settings=default_mahjong_playbooks().get(3,"atk","south").thresholds_for("D1")
    settings["attack_completion"]=False
    base={"shanten":1,"projected_han":3,"route_cost":0,"effective_ukeire":8,"ukeire":8,
          "dora_loss":0,"pair_break_loss":0,"wait_value":None,"target_route":"riichi"}
    return board,settings,[dict(base,action={"kind":"discard","tile":t}) for t in ("2p","5p")]


def test_proven_riichi_safe_tile_breaks_only_a_complete_offensive_tie():
    board,settings,options=setup()
    assert offensive(board,options,settings)["action"]["tile"]=="2p"


@pytest.mark.parametrize("field,value",[("projected_han",2),("effective_ukeire",7),("shanten",2),
                                       ("dora_loss",1),("pair_break_loss",1)])
def test_genbutsu_never_trades_off_an_existing_attack_criterion(field,value):
    board,settings,options=setup();options[0][field]=value
    assert offensive(board,options,settings)["action"]["tile"]=="5p"


def test_every_riichi_declarer_must_have_discarded_the_tile():
    board,settings,options=setup();board["players"][2]["riichi"]="declared"
    assert not riichi_genbutsu(board,"2p")
    board["players"][2]["discards"]=[{"tile":"2p"}]
    assert riichi_genbutsu(board,"2p")


def test_no_riichi_keeps_original_draw_discard_tiebreak():
    board,settings,options=setup();board["players"][1]["riichi"]="none"
    assert not riichi_genbutsu(board,"2p")
    assert offensive(board,options,settings)["action"]["tile"]=="5p"


def test_red_and_regular_five_share_genbutsu_identity():
    board,_,_=setup();board["players"][1]["discards"]=[{"tile":"0p"}]
    assert riichi_genbutsu(board,"5p")
