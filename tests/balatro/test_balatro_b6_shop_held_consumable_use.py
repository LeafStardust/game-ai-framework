from pathlib import Path
from types import SimpleNamespace

import pytest

from games.balatro.actions import END_SHOP, USE_CONSUMABLE, BalatroAction
from games.balatro.live.consumable_timing import HOLD, USE, LiveConsumableTimingPolicy
from games.balatro.live.external.live_memory_autonomous_step_injected import (
    LiveMemoryInjectedSingleStepRunner,
)
from games.balatro.live.injected.action_dispatcher import (
    LiveMemoryInjectedActionDispatcher,
)
from games.balatro.live.injected.bridge import FirstPartyBalatroBridge
from games.balatro.live.injected.hand_dispatcher import UnsupportedInjectedHandAction
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.state import BalatroState
from games.balatro.tarots import Hermit, Strength


class _Observer:
    def __init__(self, snapshots):
        if isinstance(snapshots, LiveBalatroSnapshot):
            snapshots = [snapshots]
        self.snapshots = list(snapshots)
        self.calls = 0

    def observe(self):
        self.calls += 1
        if len(self.snapshots) > 1:
            return self.snapshots.pop(0)
        return self.snapshots[0]


class _Translator:
    def __init__(self, state):
        self.state = state

    def translate(self, snapshot):
        return self.state


class _RecordingBridge(FirstPartyBalatroBridge):
    def __init__(self):
        self.calls = []

    def _call(self, action, indices=()):
        self.calls.append((action, tuple(indices)))
        return "accepted"


def _shop_state(consumable, *, money=10, slots=2):
    state = BalatroState()
    state.phase = "SHOP"
    state.hand = []
    state.money = money
    state.consumables = [consumable]
    state.consumable_slots = slots
    return state


def _shop_snapshot(sequence, consumable_ids, *, complete=True):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase="SHOP",
        state_complete=complete,
        payload={
            "consumables": {
                "cards": [
                    {"live_id": live_id, "area_index": index}
                    for index, live_id in enumerate(consumable_ids)
                ]
            }
        },
    )


def test_shop_timing_uses_peak_hermit_without_hand_target():
    hermit = Hermit()
    state = _shop_state(hermit, money=10)

    recommendation = LiveConsumableTimingPolicy().recommend(state, hermit)

    assert recommendation.decision == USE
    assert recommendation.target is None
    assert recommendation.immediate_gain == 10.0
    action = recommendation.to_action()
    assert action is not None
    assert action.name == USE_CONSUMABLE
    assert action.cards == []
    assert action.target is hermit


def test_shop_timing_keeps_targeted_consumables_fail_closed():
    strength = Strength()
    state = _shop_state(strength)

    recommendation = LiveConsumableTimingPolicy().recommend(state, strength)

    assert recommendation.decision == HOLD
    assert not recommendation.should_use
    assert recommendation.target is None
    assert any(
        "SHOP timing admits only validated no-hand-target" in note
        for note in recommendation.rationale
    )


def test_autonomous_shop_uses_held_consumable_before_shop_arbiter():
    hermit = Hermit()
    state = _shop_state(hermit, money=10)
    snapshot = _shop_snapshot(10, [501])

    def shop_should_not_run(state_value, snapshot_value):
        raise AssertionError("shop arbiter must not run after B6 chooses USE_CONSUMABLE")

    decision = LiveMemoryInjectedSingleStepRunner(
        _Observer(snapshot),
        translator=_Translator(state),
        bridge=SimpleNamespace(),
        dispatcher=SimpleNamespace(),
        shop_recommender=shop_should_not_run,
        pack_choice_reader=lambda: (),
    ).decide()

    assert decision.action.name == USE_CONSUMABLE
    assert decision.action.target is hermit
    assert decision.source == "B6 consumable timing policy"
    assert decision.notes[:3] == (
        "shop_decision=USE_CONSUMABLE",
        "consumable=The Hermit",
        "target_indices=()",
    )


def test_autonomous_shop_hold_falls_through_to_shop_arbiter():
    hermit = Hermit()
    state = _shop_state(hermit, money=6, slots=2)
    snapshot = _shop_snapshot(20, [501])
    shop_action = BalatroAction(END_SHOP)
    calls = []

    def shop_recommender(state_value, snapshot_value):
        calls.append((state_value, snapshot_value))
        return shop_action, ("shop-note",)

    decision = LiveMemoryInjectedSingleStepRunner(
        _Observer(snapshot),
        translator=_Translator(state),
        bridge=SimpleNamespace(),
        dispatcher=SimpleNamespace(),
        shop_recommender=shop_recommender,
        pack_choice_reader=lambda: (),
    ).decide()

    assert len(calls) == 1
    assert decision.action is shop_action
    assert decision.source == "shop policy"
    assert decision.notes == ("shop-note",)


def test_unified_dispatcher_executes_shop_safe_no_target_held_consumable():
    consumable = SimpleNamespace(live_id=501, name="The Hermit")
    state = SimpleNamespace(hand=[], consumables=[consumable])
    before = _shop_snapshot(30, [501])
    transient_wrong_phase = LiveBalatroSnapshot(
        sequence=31,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={"consumables": {"cards": []}},
    )
    settled = _shop_snapshot(32, [])
    observer = _Observer([transient_wrong_phase, settled])
    bridge = _RecordingBridge()
    action = BalatroAction(USE_CONSUMABLE, target=consumable)

    result = LiveMemoryInjectedActionDispatcher(
        observer,
        bridge=bridge,
        timeout=0.1,
        poll_interval=0,
    ).dispatch(action, state=state, snapshot=before)

    assert bridge.calls == [("USE_CONSUMABLE", (0,))]
    assert observer.calls == 2
    assert result.after is settled
    assert result.details == {
        "consumable_index": 0,
        "target_indices": (),
        "consumed_live_id": 501,
    }


def test_shop_dispatcher_rejects_hand_targets_and_unvalidated_consumables():
    card = SimpleNamespace(live_id=101)
    hermit = SimpleNamespace(live_id=501, name="The Hermit")
    strength = SimpleNamespace(live_id=502, name="Strength")
    before = _shop_snapshot(40, [501])
    bridge = _RecordingBridge()

    with pytest.raises(UnsupportedInjectedHandAction, match="cannot include hand targets"):
        LiveMemoryInjectedActionDispatcher(
            _Observer(before),
            bridge=bridge,
            timeout=0,
            poll_interval=0,
        ).dispatch(
            BalatroAction(USE_CONSUMABLE, cards=[card], target=hermit),
            state=SimpleNamespace(hand=[card], consumables=[hermit]),
            snapshot=before,
        )

    unsupported_before = _shop_snapshot(50, [502])
    with pytest.raises(UnsupportedInjectedHandAction, match="not validated for Strength"):
        LiveMemoryInjectedActionDispatcher(
            _Observer(unsupported_before),
            bridge=bridge,
            timeout=0,
            poll_interval=0,
        ).dispatch(
            BalatroAction(USE_CONSUMABLE, target=strength),
            state=SimpleNamespace(hand=[], consumables=[strength]),
            snapshot=unsupported_before,
        )

    assert bridge.calls == []


def test_first_party_lua_bridge_fail_closes_shop_held_use_to_validated_centers():
    bridge_lua = Path(
        "games/balatro/live/injected/assets/bridge.lua"
    ).read_text(encoding="utf-8")

    assert "G.STATE == G.STATES.SHOP" in bridge_lua
    assert "SHOP held-consumable use cannot include hand targets" in bridge_lua
    assert 'key ~= "c_hermit"' in bridge_lua
    assert 'key ~= "c_temperance"' in bridge_lua
    assert 'key ~= "c_wheel_of_fortune"' in bridge_lua
