import pytest

from games.balatro.actions import USE_CONSUMABLE, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.live.injected.bridge import FirstPartyBalatroBridge
from games.balatro.live.injected.consumable_target_postcondition import (
    build_consumable_target_postcondition,
)
from games.balatro.live.injected.hand_dispatcher import (
    LiveMemoryInjectedHandDispatcher,
)
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.planets import create_planet
from games.balatro.state import BalatroState


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


def _snapshot(sequence, consumable_ids, *, pair_level, complete=True):
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
            "hands": {
                "Pair": {
                    "level": pair_level,
                    "played": 0,
                }
            },
            "round": {"hands_left": 4, "discards_left": 3},
        },
    )


def _state_with_mercury():
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [BalatroCard("8", "Hearts"), BalatroCard("8", "Clubs")]
    mercury = create_planet("MERCURY")
    mercury.live_id = 501
    state.consumables = [mercury]
    state.hand_levels["PAIR"] = 1
    return state, mercury


def test_held_planet_waits_for_authoritative_hand_level_increment():
    state, mercury = _state_with_mercury()
    before = _snapshot(10, [501], pair_level=1)
    disappeared_only = _snapshot(11, [], pair_level=1)
    settled = _snapshot(12, [], pair_level=2)
    observer = _Observer([disappeared_only, settled])
    bridge = _RecordingBridge()
    action = BalatroAction(USE_CONSUMABLE, target=mercury)

    result = LiveMemoryInjectedHandDispatcher(
        observer,
        bridge=bridge,
        timeout=0.1,
        poll_interval=0,
    ).dispatch(action, state=state, snapshot=before)

    assert bridge.calls == [("USE_CONSUMABLE", (0,))]
    assert observer.calls == 2
    assert result.after is settled
    assert result.details["consumed_live_id"] == 501
    assert result.details["target_indices"] == ()
    assert result.details["verified_target_live_ids"] == ()


def test_planet_postcondition_matches_normalized_or_internal_hand_key():
    state, _ = _state_with_mercury()
    postcondition = build_consumable_target_postcondition(
        state,
        consumable_index=0,
        target_indices=(),
    )

    assert postcondition is not None
    assert postcondition.expected_hand_level == ("PAIR", 2)
    assert not postcondition.matches(_snapshot(11, [], pair_level=1))
    assert postcondition.matches(_snapshot(12, [], pair_level=2))

    internal_key_snapshot = LiveBalatroSnapshot(
        sequence=13,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={"hands": {"PAIR": {"level": 2}}},
    )
    assert postcondition.matches(internal_key_snapshot)


def test_planet_verification_rejects_hand_targets():
    state, _ = _state_with_mercury()

    with pytest.raises(ValueError, match="does not accept hand targets"):
        build_consumable_target_postcondition(
            state,
            consumable_index=0,
            target_indices=(0,),
        )
