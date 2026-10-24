from copy import deepcopy
import pytest
from games.mahjong_soul.live.runtime.decision import offered_actions,decision_request
from agents.mahjong_soul.policy import make_policy


def report():
    # Synthetic legal opening offer; no live connection, room or account data.
    from tests.mahjong_soul.test_sanma_south_attack import south
    r=south("19m19p19s1234567z2p")
    r["state"]["operations"]["operation_list"]=[
        {"type":1,"combination":[]},{"type":11,"combination":[]},
        {"type":10,"combination":[]}]
    return r


def test_nine_terminals_offer_keeps_discard_and_kita_available():
    r=report();before=deepcopy(r);actions=offered_actions(r)
    assert any(a["kind"]=="discard" for a in actions)
    assert {"kind":"extract_north","tile":"4z"} in actions
    assert not any(a["kind"]=="abort_draw" for a in actions)
    choice=make_policy("playbook","atk").choose(decision_request(r))
    assert choice in actions and choice["kind"] in ("discard","extract_north")
    assert r==before


def test_unknown_duplicate_or_malformed_abort_stays_rejected():
    for offers in ([{"type":10}], [{"type":1},{"type":10,"combination":["1m"]}],
                   [{"type":1},{"type":10},{"type":10}], [{"type":1},{"type":99}]):
        r=report();r["state"]["operations"]["operation_list"]=offers
        with pytest.raises(ValueError):offered_actions(r)
