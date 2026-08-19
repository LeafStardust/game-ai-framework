from __future__ import annotations

from types import SimpleNamespace

import pytest

from games.balatro.actions import (
    END_ROUND,
    END_SHOP,
    PLAY_CARDS,
    SELECT_BLIND,
    SELECT_PACK_CARD,
    SKIP_BLIND,
    BalatroAction,
)
from games.balatro.live.external.live_memory_autonomous_step_injected import (
    AutonomousBridgeCapabilityError,
    AutonomousStepDecision,
    AutonomousStepGuardError,
    LiveMemoryInjectedSingleStepRunner,
    UnsupportedAutonomousPhase,
    _pack_choice_signature,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


def _snapshot(sequence: int, phase: str, *, marker: int = 1) -> LiveBalatroSnapshot:
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=True,
        payload={"marker": marker},
    )


class FakeObserver:
    def __init__(self, *snapshots):
        self.snapshots = list(snapshots)
        self.last = snapshots[-1] if snapshots else None

    def observe(self):
        if self.snapshots:
            self.last = self.snapshots.pop(0)
        return self.last


class FakeTranslator:
    def __init__(self, state):
        self.state = state

    def translate(self, snapshot):
        return self.state


class FakeBridge:
    def __init__(
        self,
        *,
        gate="ENABLED",
        version="1",
        blind_skip=None,
        revision="2",
    ):
        self.gate = gate
        self.version = version
        self.blind_skip = blind_skip
        self.revision = revision
        self.status_calls = 0

    def status(self):
        self.status_calls += 1
        status = {
            "bridge": self.version,
            "achievement_gate": self.gate,
            "bridge_revision": self.revision,
        }
        if self.blind_skip is not None:
            status["blind_skip"] = self.blind_skip
        return status


class FakeDispatcher:
    def __init__(self, after):
        self.after = after
        self.calls = []

    def dispatch(self, action, *, state=None, snapshot=None):
        self.calls.append((action, state, snapshot))
        return SimpleNamespace(after=self.after)


def _state(phase: str, *, hand=None):
    return SimpleNamespace(
        phase=phase,
        hand=list(hand or []),
    )


def test_autonomous_round_eval_recommends_cash_out():
    before = _snapshot(1, "ROUND_EVAL")
    runner = LiveMemoryInjectedSingleStepRunner(
        FakeObserver(before),
        translator=FakeTranslator(_state("ROUND_EVAL")),
        bridge=FakeBridge(),
        dispatcher=FakeDispatcher(_snapshot(2, "SHOP")),
    )

    decision = runner.decide()

    assert decision.action.name == END_ROUND
    assert decision.source == "deterministic round-flow policy"


def test_autonomous_blind_select_recommends_current_blind():
    before = _snapshot(1, "BLIND_SELECT")
    runner = LiveMemoryInjectedSingleStepRunner(
        FakeObserver(before),
        translator=FakeTranslator(_state("BLIND_SELECT")),
        bridge=FakeBridge(),
        dispatcher=FakeDispatcher(_snapshot(2, "SELECTING_HAND")),
    )

    decision = runner.decide()

    assert decision.action.name == SELECT_BLIND
    assert decision.source == "D13 blind play-vs-skip policy"
    assert "blind_decision=PLAY" in decision.notes
    assert "tag_value_source=fallback_unidentified_live_tag" in decision.notes


def test_autonomous_hand_uses_injected_d1_recommendation():
    before = _snapshot(1, "SELECTING_HAND")
    card = object()
    state = _state("SELECTING_HAND", hand=[card])
    action = BalatroAction(PLAY_CARDS, cards=[card])
    runner = LiveMemoryInjectedSingleStepRunner(
        FakeObserver(before),
        translator=FakeTranslator(state),
        bridge=FakeBridge(),
        dispatcher=FakeDispatcher(_snapshot(2, "SELECTING_HAND")),
        hand_recommender=lambda current, snapshot: (
            action,
            ("mode=CLEAR_PATH", "indices=(0,)",),
        ),
    )

    decision = runner.decide()

    assert decision.action is action
    assert decision.source == "D1 hand-action policy"
    assert "mode=CLEAR_PATH" in decision.notes


def test_autonomous_shop_uses_policy_recommendation():
    before = _snapshot(3, "SHOP")
    action = BalatroAction(END_SHOP)
    runner = LiveMemoryInjectedSingleStepRunner(
        FakeObserver(before),
        translator=FakeTranslator(_state("SHOP")),
        bridge=FakeBridge(),
        dispatcher=FakeDispatcher(_snapshot(4, "BLIND_SELECT")),
        shop_recommender=lambda current, snapshot: (
            action,
            ("policy_score=1.0",),
        ),
    )

    decision = runner.decide()

    assert decision.action.name == END_SHOP
    assert decision.source == "shop policy"


def test_autonomous_runner_blocks_unvalidated_phase():
    before = _snapshot(1, "MENU")
    runner = LiveMemoryInjectedSingleStepRunner(
        FakeObserver(before),
        translator=FakeTranslator(_state("MENU")),
        bridge=FakeBridge(),
        dispatcher=FakeDispatcher(before),
    )

    with pytest.raises(UnsupportedAutonomousPhase, match="MENU"):
        runner.decide()


def test_autonomous_execute_dispatches_exactly_one_gameplay_action():
    before = _snapshot(10, "SHOP")
    after = _snapshot(11, "BLIND_SELECT")
    observer = FakeObserver(before, before, before)
    bridge = FakeBridge()
    dispatcher = FakeDispatcher(after)
    action = BalatroAction(END_SHOP)
    runner = LiveMemoryInjectedSingleStepRunner(
        observer,
        translator=FakeTranslator(_state("SHOP")),
        bridge=bridge,
        dispatcher=dispatcher,
        shop_recommender=lambda current, snapshot: (action, ()),
    )
    decision = runner.decide()

    result, status = runner.execute(decision)

    assert result.after is after
    assert status["achievement_gate"] == "ENABLED"
    assert bridge.status_calls == 1
    assert len(dispatcher.calls) == 1
    dispatched_action, _, dispatched_snapshot = dispatcher.calls[0]
    assert dispatched_action is action
    assert dispatched_snapshot is before


def test_autonomous_execute_blocks_stale_public_state_before_status():
    before = _snapshot(20, "SHOP", marker=1)
    changed = _snapshot(21, "SHOP", marker=2)
    bridge = FakeBridge()
    dispatcher = FakeDispatcher(_snapshot(22, "BLIND_SELECT"))
    runner = LiveMemoryInjectedSingleStepRunner(
        FakeObserver(before, changed),
        translator=FakeTranslator(_state("SHOP")),
        bridge=bridge,
        dispatcher=dispatcher,
        shop_recommender=lambda current, snapshot: (BalatroAction(END_SHOP), ()),
    )
    decision = runner.decide()

    with pytest.raises(AutonomousStepGuardError, match="state changed"):
        runner.execute(decision)

    assert bridge.status_calls == 0
    assert dispatcher.calls == []


def test_autonomous_execute_blocks_disabled_achievement_gate():
    before = _snapshot(30, "SHOP")
    bridge = FakeBridge(gate="DISABLED")
    dispatcher = FakeDispatcher(_snapshot(31, "BLIND_SELECT"))
    runner = LiveMemoryInjectedSingleStepRunner(
        FakeObserver(before, before),
        translator=FakeTranslator(_state("SHOP")),
        bridge=bridge,
        dispatcher=dispatcher,
        shop_recommender=lambda current, snapshot: (BalatroAction(END_SHOP), ()),
    )
    decision = runner.decide()

    with pytest.raises(AutonomousStepGuardError, match="NO_ACHIEVEMENTS"):
        runner.execute(decision)

    assert bridge.status_calls == 1
    assert dispatcher.calls == []


def test_autonomous_skip_blind_blocks_stale_bridge_before_gameplay_dispatch():
    before = _snapshot(35, "BLIND_SELECT")
    bridge = FakeBridge(blind_skip=None, revision="2")
    dispatcher = FakeDispatcher(_snapshot(36, "BLIND_SELECT"))
    state = _state("BLIND_SELECT")
    runner = LiveMemoryInjectedSingleStepRunner(
        FakeObserver(before, before),
        translator=FakeTranslator(state),
        bridge=bridge,
        dispatcher=dispatcher,
    )
    decision = AutonomousStepDecision(
        snapshot=before,
        state=state,
        action=BalatroAction(SKIP_BLIND),
        source="D13 blind play-vs-skip policy",
    )

    with pytest.raises(
        AutonomousBridgeCapabilityError,
        match="does not advertise SKIP_BLIND support",
    ):
        runner.execute(decision)

    assert bridge.status_calls == 1
    assert dispatcher.calls == []


def test_autonomous_skip_blind_dispatches_when_bridge_advertises_capability():
    before = _snapshot(37, "BLIND_SELECT")
    after = _snapshot(38, "BLIND_SELECT")
    bridge = FakeBridge(blind_skip="1", revision="3")
    dispatcher = FakeDispatcher(after)
    state = _state("BLIND_SELECT")
    runner = LiveMemoryInjectedSingleStepRunner(
        FakeObserver(before, before),
        translator=FakeTranslator(state),
        bridge=bridge,
        dispatcher=dispatcher,
    )
    decision = AutonomousStepDecision(
        snapshot=before,
        state=state,
        action=BalatroAction(SKIP_BLIND),
        source="D13 blind play-vs-skip policy",
    )

    result, status = runner.execute(decision)

    assert result.after is after
    assert status["blind_skip"] == "1"
    assert bridge.status_calls == 1
    assert len(dispatcher.calls) == 1
    assert dispatcher.calls[0][0] is decision.action


def test_autonomous_pack_blocks_changed_visible_choice_identity():
    before = _snapshot(40, "PLANET_PACK")
    first = SimpleNamespace(
        area_index=0,
        address=100,
        kind="PLANET",
        label="Mars",
        data={"center": "c_mars"},
    )
    changed = SimpleNamespace(
        area_index=0,
        address=200,
        kind="PLANET",
        label="Jupiter",
        data={"center": "c_jupiter"},
    )
    first_signature = _pack_choice_signature((first,))
    action = BalatroAction(SELECT_PACK_CARD, target={"area_index": 0})
    bridge = FakeBridge()
    dispatcher = FakeDispatcher(_snapshot(41, "SHOP"))
    runner = LiveMemoryInjectedSingleStepRunner(
        FakeObserver(before, before),
        translator=FakeTranslator(_state("PLANET_PACK")),
        bridge=bridge,
        dispatcher=dispatcher,
        pack_recommender=lambda current, snapshot: (
            action,
            ("policy_score=2.0",),
            first_signature,
        ),
        pack_choice_reader=lambda: (changed,),
    )
    decision = runner.decide()

    with pytest.raises(AutonomousStepGuardError, match="booster-pack choices changed"):
        runner.execute(decision)

    assert bridge.status_calls == 0
    assert dispatcher.calls == []
