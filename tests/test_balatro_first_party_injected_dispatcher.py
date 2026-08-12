from types import SimpleNamespace

from games.balatro.actions import (
    DISCARD_CARDS,
    PLAY_CARDS,
    BalatroAction,
)
from games.balatro.card import BalatroCard
from games.balatro.live.injected.hand_dispatcher import (
    LiveMemoryInjectedHandDispatcher,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


class FakeBridge:
    def __init__(self):
        self.calls = []

    def play(self, indices):
        self.calls.append(("play", tuple(indices)))

    def discard(self, indices):
        self.calls.append(("discard", tuple(indices)))


class FakeObserver:
    def __init__(self, *snapshots):
        self.snapshots = list(snapshots)

    def observe(self):
        return self.snapshots.pop(0)


def _state():
    hand = [
        BalatroCard("A", "Spades", live_id=100),
        BalatroCard("K", "Hearts", live_id=200),
        BalatroCard("Q", "Clubs", live_id=300),
    ]
    return SimpleNamespace(hand=hand)


def test_injected_dispatcher_plays_by_current_hand_position():
    state = _state()
    before = LiveBalatroSnapshot(
        sequence=10,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={"round": {"hands_left": 4, "discards_left": 3}},
    )
    after = LiveBalatroSnapshot(
        sequence=11,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={"round": {"hands_left": 3, "discards_left": 3}},
    )
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedHandDispatcher(
        FakeObserver(after),
        bridge=bridge,
        poll_interval=0,
    )

    result = dispatcher.dispatch(
        BalatroAction(
            PLAY_CARDS,
            cards=[state.hand[0], state.hand[2]],
        ),
        state=state,
        snapshot=before,
    )

    assert bridge.calls == [("play", (0, 2))]
    assert result.details == (0, 2)
    assert result.after is after


def test_injected_dispatcher_discards_by_current_hand_position():
    state = _state()
    before = LiveBalatroSnapshot(
        sequence=5,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={"round": {"hands_left": 4, "discards_left": 4}},
    )
    after = LiveBalatroSnapshot(
        sequence=6,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={"round": {"hands_left": 4, "discards_left": 3}},
    )
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedHandDispatcher(
        FakeObserver(after),
        bridge=bridge,
        poll_interval=0,
    )

    result = dispatcher.dispatch(
        BalatroAction(
            DISCARD_CARDS,
            cards=[state.hand[1]],
        ),
        state=state,
        snapshot=before,
    )

    assert bridge.calls == [("discard", (1,))]
    assert result.details == (1,)
    assert result.after is after


def test_injected_play_accepts_round_eval_semantic_checkpoint():
    state = _state()
    before = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={"round": {"hands_left": 2, "discards_left": 1}},
    )
    after = LiveBalatroSnapshot(
        sequence=2,
        phase="ROUND_EVAL",
        state_complete=True,
        payload={"round": {"hands_left": 1, "discards_left": 1}},
    )
    bridge = FakeBridge()
    dispatcher = LiveMemoryInjectedHandDispatcher(
        FakeObserver(after),
        bridge=bridge,
        poll_interval=0,
    )

    result = dispatcher.dispatch(
        BalatroAction(
            PLAY_CARDS,
            cards=[state.hand[0]],
        ),
        state=state,
        snapshot=before,
    )

    assert bridge.calls == [("play", (0,))]
    assert result.after.phase == "ROUND_EVAL"
