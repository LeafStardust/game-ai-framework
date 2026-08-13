from types import SimpleNamespace

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
from games.balatro.state import BalatroState
from games.balatro.tarots import HangedMan, Strength


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


def _raw_card(
    live_id,
    rank,
    suit="C",
    *,
    enhancement=None,
    edition=None,
    seal=None,
):
    return {
        "live_id": live_id,
        "value": {"rank": rank, "suit": suit},
        "modifier": {
            "enhancement": enhancement,
            "edition": edition,
            "seal": seal,
        },
    }


def _snapshot(sequence, consumable_ids, hand_cards):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "hand": {"cards": list(hand_cards)},
            "consumables": {
                "cards": [
                    {"live_id": live_id, "area_index": index}
                    for index, live_id in enumerate(consumable_ids)
                ]
            },
            "round": {"hands_left": 4, "discards_left": 3},
        },
    )


def _state(cards, consumable):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.consumables = [consumable]
    return state


def test_strength_postcondition_requires_exact_target_semantic_change():
    card = BalatroCard("4", "Clubs", live_id=101)
    strength = Strength()
    strength.live_id = 501
    state = _state([card], strength)

    postcondition = build_consumable_target_postcondition(
        state,
        consumable_index=0,
        target_indices=(0,),
    )

    assert postcondition is not None
    assert postcondition.live_ids == (101,)
    assert not postcondition.matches(_snapshot(11, [], [_raw_card(101, "4")]))
    assert postcondition.matches(_snapshot(12, [], [_raw_card(101, "5")]))


def test_dispatcher_waits_for_target_change_after_consumable_disappears():
    card = BalatroCard("4", "Clubs", live_id=101)
    strength = Strength()
    strength.live_id = 501
    state = _state([card], strength)
    before = _snapshot(20, [501], [_raw_card(101, "4")])
    consumed_but_unresolved = _snapshot(21, [], [_raw_card(101, "4")])
    settled = _snapshot(22, [], [_raw_card(101, "5")])
    observer = _Observer([consumed_but_unresolved, settled])
    bridge = _RecordingBridge()
    action = BalatroAction(USE_CONSUMABLE, cards=[card], target=strength)

    result = LiveMemoryInjectedHandDispatcher(
        observer,
        bridge=bridge,
        timeout=0.1,
        poll_interval=0,
    ).dispatch(action, state=state, snapshot=before)

    assert bridge.calls == [("USE_CONSUMABLE", (0, 0))]
    assert observer.calls == 2
    assert result.after is settled
    assert result.details["verified_target_live_ids"] == (101,)


def test_hanged_man_postcondition_verifies_both_selected_live_ids_are_gone():
    first = BalatroCard("2", "Hearts", live_id=101)
    second = BalatroCard("3", "Clubs", live_id=102)
    survivor = BalatroCard("A", "Spades", live_id=103)
    hanged_man = HangedMan()
    hanged_man.live_id = 501
    state = _state([first, second, survivor], hanged_man)

    postcondition = build_consumable_target_postcondition(
        state,
        consumable_index=0,
        target_indices=(0, 1),
    )

    assert postcondition is not None
    assert postcondition.live_ids == (101, 102)
    assert not postcondition.matches(
        _snapshot(31, [], [_raw_card(102, "3"), _raw_card(103, "A", "S")])
    )
    assert postcondition.matches(
        _snapshot(32, [], [_raw_card(103, "A", "S")])
    )


def test_unknown_targeted_consumable_keeps_legacy_consumption_postcondition():
    card = SimpleNamespace(live_id=101)
    consumable = SimpleNamespace(live_id=501, name="unsupported")
    state = SimpleNamespace(hand=[card], consumables=[consumable])

    assert build_consumable_target_postcondition(
        state,
        consumable_index=0,
        target_indices=(0,),
    ) is None
