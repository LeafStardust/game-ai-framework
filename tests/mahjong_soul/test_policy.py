from copy import deepcopy
import pytest

from agents.mahjong_soul.policy import BaselinePolicy, proposal_from_policy
from agents.mahjong_soul.evaluate import decide, evaluate_capture
from games.mahjong_soul.live.runtime.decision import decision_request
from tests.mahjong_soul.test_input import inputs
from tests.mahjong_soul.test_calls import offer as pon_offer
from tests.mahjong_soul.test_win_input import offer as win_offer


def test_baseline_takes_win_before_discard():
    report, _ = win_offer()
    assert decide(BaselinePolicy(), report, lambda:report)["action"] == {"kind":"tsumo","tile":"0p"}


def test_baseline_discard_draw_and_skip_calls_without_coordinates():
    report, _ = inputs(); report["state"]["hand"] = ["0p","1m"]
    report["state"]["drawn_tile"] = "1m"
    assert decide(BaselinePolicy(), report, lambda:report)["action"] == {"kind":"discard","tile":"1m"}
    report["state"]["operations"]["operation_list"][0]["combination"] = ["1m"]
    assert decide(BaselinePolicy(), report, lambda:report)["action"] == {"kind":"discard","tile":"0p"}
    call, _ = pon_offer()
    assert decide(BaselinePolicy(), call, lambda:call)["action"] == {"kind":"skip"}


def test_baseline_is_deterministic_and_preserves_red_tile_when_tied():
    report, _ = inputs(); report["state"]["hand"] = ["0p","5p","1m"]
    request = decision_request(report)
    original = deepcopy(request)
    policy = BaselinePolicy()
    assert policy.choose(request) == policy.choose(request) == {"kind":"discard","tile":"1m"}
    assert request == original


@pytest.mark.parametrize("behavior", ["mutate","invalid","wrong_type","exception"])
def test_bad_policy_cannot_change_validator_request_or_get_authorized(behavior):
    report, _ = inputs(); request = decision_request(report, now=10)
    original = deepcopy(request)
    class Bad:
        def choose(self, value):
            if behavior == "exception": raise RuntimeError("bad policy")
            if behavior == "wrong_type": return None
            if behavior == "mutate":
                value["request_id"] = "fake"; value["actions"].append({"kind":"discard","tile":"1m"})
            return {"kind":"discard","tile":"1m"}
    with pytest.raises((ValueError,RuntimeError)):
        decide(Bad(), report, lambda:report)
    assert request == original


def test_adapter_rechecks_current_board_and_policy_elapsed_time():
    report, _ = inputs(); changed = deepcopy(report); changed["game_generation"] += 1
    with pytest.raises(ValueError): decide(BaselinePolicy(), report, lambda:changed)
    ticks = iter([10,13])
    with pytest.raises(ValueError, match="expired"):
        decide(BaselinePolicy(), report, lambda:report, clock=lambda:next(ticks))


def test_evaluator_deduplicates_states_and_counts_failures_without_input(monkeypatch):
    import agents.mahjong_soul.evaluate as module
    report, _ = inputs(); call, _ = pon_offer()
    unsupported = deepcopy(call); unsupported["state"]["step"] = 9
    unsupported["state"]["operations"]["operation_list"] = [{"type":11}]
    closed = deepcopy(report); closed["connection_open"] = False
    class Reader:
        def __init__(self, schema): self.report = None
        def consume(self, row):
            if row == "bad": raise ValueError("bad capture")
            self.report = deepcopy(row)
        def snapshot(self): return deepcopy(self.report)
    monkeypatch.setattr(module, "GameReader", Reader)
    result = evaluate_capture([report,report,call,unsupported,"bad",closed], None)
    assert result["unique_decision_boards"] == 3
    assert result["validated_proposals"] == 2
    assert result["chosen_actions"] == {"discard":1,"skip":1}
    assert result["malformed_rows"] == 1
    assert sum(result["unsupported_requests"].values()) == 1
    assert result["executable"] is False and not result["connection_open_at_end"]
    class Crash:
        def choose(self, request): raise RuntimeError("no fallback")
    result = evaluate_capture([report], None, Crash())
    assert result["policy_failures"] == 1 and result["validated_proposals"] == 0
    assert result["policy_failure_types"] == {"RuntimeError":1}


def test_adapter_gives_policy_an_independent_request_copy():
    report, _ = inputs(); request = decision_request(report, now=10)
    original = deepcopy(request)
    class Mutating:
        def choose(self, value):
            action = deepcopy(value["actions"][0])
            value["request_id"] = "changed"
            value["observation"]["board"]["self"]["hand"].clear()
            value["actions"].clear()
            return action
    proposal = proposal_from_policy(Mutating(), request)
    assert request == original
    assert proposal["request_id"] == original["request_id"]
    assert proposal["action"] == original["actions"][0]
