from types import SimpleNamespace

import pytest

from games.balatro.actions import USE_CONSUMABLE, BalatroAction
from games.balatro.live.injected.action_dispatcher import (
    LiveMemoryInjectedActionDispatcher,
)
from games.balatro.live.injected.bridge import FirstPartyBalatroBridge
from games.balatro.live.injected.hand_dispatcher import (
    LiveMemoryInjectedHandDispatcher,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


class _RecordingBridge(FirstPartyBalatroBridge):
    def __init__(self):
        self.calls = []

    def _call(self, action, indices=()):
        self.calls.append((action, tuple(indices)))
        return "accepted"


class _Observer:
    def __init__(self, snapshots):
        self.snapshots = list(snapshots)
        self.calls = 0

    def observe(self):
        self.calls += 1
        if len(self.snapshots) > 1:
            return self.snapshots.pop(0)
        return self.snapshots[0]


def _snapshot(sequence, consumable_ids, *, complete=True):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase="SELECTING_HAND",
        state_complete=complete,
        payload={
            "consumables": {
                "cards": [
                    {"live_id": live_id, "area_index": index}
                    for index, live_id in enumerate(consumable_ids)
                ]
            },
            "round": {"hands_left": 4, "discards_left": 3},
        },
    )


def _state():
    card = SimpleNamespace(live_id=101)
    consumable = SimpleNamespace(live_id=501)
    return SimpleNamespace(hand=[card], consumables=[consumable]), card, consumable


def test_bridge_encodes_consumable_slot_and_hand_targets_as_separate_index_spaces():
    bridge = _RecordingBridge()

    bridge.use_consumable(0, (0, 2))

    assert bridge.calls == [("USE_CONSUMABLE", (0, 0, 2))]


def test_bridge_rejects_duplicate_hand_targets_but_allows_no_target_consumable():
    bridge = _RecordingBridge()

    bridge.use_consumable(1)
    assert bridge.calls == [("USE_CONSUMABLE", (1,))]

    with pytest.raises(ValueError, match="duplicates"):
        bridge.use_consumable(1, (0, 0))


def test_hand_dispatcher_waits_for_exact_consumable_live_id_to_disappear():
    state, card, consumable = _state()
    before = _snapshot(10, [501])
    transient = _snapshot(11, [501])
    settled = _snapshot(12, [])
    observer = _Observer([transient, settled])
    bridge = _RecordingBridge()
    action = BalatroAction(USE_CONSUMABLE, cards=[card], target=consumable)

    result = LiveMemoryInjectedHandDispatcher(
        observer,
        bridge=bridge,
        timeout=0.1,
        poll_interval=0,
    ).dispatch(action, state=state, snapshot=before)

    assert bridge.calls == [("USE_CONSUMABLE", (0, 0))]
    assert observer.calls == 2
    assert result.after is settled
    assert result.details == {
        "consumable_index": 0,
        "target_indices": (0,),
        "consumed_live_id": 501,
    }


def test_unified_dispatcher_executes_no_target_held_consumable():
    state, _, consumable = _state()
    before = _snapshot(20, [501])
    settled = _snapshot(21, [])
    observer = _Observer([settled])
    bridge = _RecordingBridge()
    action = BalatroAction(USE_CONSUMABLE, target=consumable)

    result = LiveMemoryInjectedActionDispatcher(
        observer,
        bridge=bridge,
        timeout=0.1,
        poll_interval=0,
    ).dispatch(action, state=state, snapshot=before)

    assert bridge.calls == [("USE_CONSUMABLE", (0,))]
    assert result.after is settled
    assert result.details["target_indices"] == ()
