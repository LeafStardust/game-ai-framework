from __future__ import annotations

from types import SimpleNamespace

import pytest

from games.balatro.actions import REORDER_JOKERS
from games.balatro.joker_order_policy import JokerOrderDecision, JokerOrderPolicy
from games.balatro.live.runtime.live_memory_autonomous_step_injected import LiveMemoryInjectedSingleStepRunner
from games.balatro.live_joker_order_authority import (
    _ReplayObserver,
    _copy_order_violations,
    _identity_xmult_factor,
)


class BlueprintJoker:
    pass


class BrainstormJoker:
    pass


class PlainJoker:
    pass


class BlackboardJoker:
    pass


class AdditiveJoker:
    pass


def test_blueprint_cannot_be_last_when_another_joker_exists() -> None:
    jokers = (PlainJoker(), BlueprintJoker())

    assert _copy_order_violations(jokers, (0, 1)) == (
        "Blueprint has no Joker immediately to its right",
    )
    assert _copy_order_violations(jokers, (1, 0)) == ()


def test_live_center_key_blueprint_cannot_be_last() -> None:
    jokers = (SimpleNamespace(center="j_joker"), SimpleNamespace(center="j_blueprint"))

    assert _copy_order_violations(jokers, (0, 1)) == (
        "Blueprint has no Joker immediately to its right",
    )


def test_brainstorm_cannot_be_leftmost_when_another_joker_exists() -> None:
    jokers = (BrainstormJoker(), PlainJoker())

    assert _copy_order_violations(jokers, (0, 1)) == (
        "Brainstorm is leftmost and therefore has no leftmost target",
    )
    assert _copy_order_violations(jokers, (1, 0)) == ()


def test_useful_copy_chains_remain_legal() -> None:
    jokers = (BlueprintJoker(), BrainstormJoker(), PlainJoker())

    assert _copy_order_violations(jokers, (0, 1, 2)) == ()
    assert _copy_order_violations(jokers, (0, 2, 1)) == ()


def test_identity_based_xmult_detection_restores_right_alignment_without_public_xmult() -> None:
    additive = AdditiveJoker()
    xmult = BlackboardJoker()

    assert _identity_xmult_factor(additive) == pytest.approx(1.0)
    assert _identity_xmult_factor(xmult) > 1.0
    assert (
        JokerOrderPolicy._xmult_right_alignment((xmult, additive), (0, 1))[1]
        < JokerOrderPolicy._xmult_right_alignment((xmult, additive), (1, 0))[1]
    )


class _Observer:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.calls = 0

    def observe(self):
        self.calls += 1
        return self.snapshot


class _Translator:
    def __init__(self, state):
        self.state = state
        self.calls = 0

    def translate(self, snapshot):
        self.calls += 1
        return self.state


class _OrderPolicy:
    def __init__(self, decision):
        self.decision = decision
        self.calls = []

    def recommend(self, state, *, phase=None):
        self.calls.append((state, phase))
        return self.decision


def _ordering_decision() -> JokerOrderDecision:
    return JokerOrderDecision(
        permutation=(1, 0),
        current_score=10.0,
        ordered_score=10.0,
        rationale=("Blueprint adjacency restored",),
    )


def test_live_runner_emits_reorder_before_normal_selecting_hand_policy() -> None:
    snapshot = SimpleNamespace(state_complete=True, phase="SELECTING_HAND")
    state = SimpleNamespace(jokers=(PlainJoker(), BlueprintJoker()), phase="SELECTING_HAND")
    runner = LiveMemoryInjectedSingleStepRunner.__new__(LiveMemoryInjectedSingleStepRunner)
    runner.observer = _Observer(snapshot)
    runner.translator = _Translator(state)
    runner.joker_order_policy = _OrderPolicy(_ordering_decision())
    runner.last_observation_seconds = 0.0
    runner.last_translation_seconds = 0.0
    runner.last_policy_seconds = 0.0

    decision = runner.decide()

    assert decision.action.name == REORDER_JOKERS
    assert decision.action.target == (1, 0)
    assert decision.source == "Joker ordering invariant"
    assert runner.joker_order_policy.calls == [(state, "SELECTING_HAND")]


def test_live_runner_can_intercept_shop_before_shop_transaction() -> None:
    snapshot = SimpleNamespace(state_complete=True, phase="SHOP")
    state = SimpleNamespace(jokers=(PlainJoker(), BlueprintJoker()), phase="SHOP")
    runner = LiveMemoryInjectedSingleStepRunner.__new__(LiveMemoryInjectedSingleStepRunner)
    runner.observer = _Observer(snapshot)
    runner.translator = _Translator(state)
    runner.joker_order_policy = _OrderPolicy(_ordering_decision())
    runner.last_observation_seconds = 0.0
    runner.last_translation_seconds = 0.0
    runner.last_policy_seconds = 0.0

    decision = runner.decide()

    assert decision.action.name == REORDER_JOKERS
    assert decision.action.target == (1, 0)
    assert runner.joker_order_policy.calls == [(state, "SHOP")]


def test_replay_observer_reuses_checkpoint_once_then_delegates() -> None:
    first = object()
    second = object()

    class _Delegate:
        def __init__(self):
            self.calls = 0

        def observe(self):
            self.calls += 1
            return second

    delegate = _Delegate()
    replay = _ReplayObserver(delegate, first)

    assert replay.observe() is first
    assert delegate.calls == 0
    assert replay.observe() is second
    assert delegate.calls == 1


def test_blind_select_without_dagger_remains_nonblocking() -> None:
    policy = JokerOrderPolicy()
    state = SimpleNamespace(phase="BLIND_SELECT", jokers=(PlainJoker(), BlueprintJoker()))

    # Existing contract: ordinary scoring order waits until the hand is visible;
    # only Ceremonial Dagger may block blind selection for a pre-blind reorder.
    assert policy.recommend(state, phase="BLIND_SELECT") is None
