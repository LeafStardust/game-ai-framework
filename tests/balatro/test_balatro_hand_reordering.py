import pytest

from games.balatro.actions import PLAY_CARDS, REORDER_HAND, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand_order_policy import HandOrderPolicy
from games.balatro.jokers.hanging_chad import HangingChadJoker
from games.balatro.live.injected.action_dispatcher import (
    LiveMemoryInjectedActionDispatcher,
    UnsupportedInjectedAction,
)
from games.balatro.live.injected.bridge import FirstPartyBalatroBridge
from games.balatro.live.injected.install import bridge_asset_path
from games.balatro.live.protocol import LiveBalatroSnapshot
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

    def observe(self):
        if len(self.snapshots) > 1:
            return self.snapshots.pop(0)
        return self.snapshots[0]


def _snapshot(sequence, live_ids, *, phase="SELECTING_HAND"):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=True,
        payload={
            "hand": {
                "count": len(live_ids),
                "cards": [
                    {"live_id": live_id, "rank": "A", "suit": "Spades"}
                    for live_id in live_ids
                ],
            }
        },
    )


def _state(cards, jokers=()):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.score = 0
    state.hands_remaining = 3
    state.discards_remaining = 0
    state.blind = Blind(BlindType.BIG, 10_000)
    state.jokers = list(jokers)
    return state


def test_bridge_client_encodes_hand_permutation():
    bridge = _RecordingBridge()

    bridge.reorder_hand((2, 0, 1))

    assert bridge.calls == [(REORDER_HAND, (2, 0, 1))]


def test_dispatcher_waits_for_exact_authoritative_hand_order():
    before = _snapshot(10, [101, 102, 103])
    unchanged = _snapshot(11, [101, 102, 103])
    settled = _snapshot(12, [103, 101, 102])
    observer = _Observer([unchanged, settled])
    bridge = _RecordingBridge()

    result = LiveMemoryInjectedActionDispatcher(
        observer,
        bridge=bridge,
        timeout=0.1,
        poll_interval=0,
    ).dispatch(
        BalatroAction(REORDER_HAND, target=(2, 0, 1)),
        snapshot=before,
    )

    assert bridge.calls == [(REORDER_HAND, (2, 0, 1))]
    assert result.after is settled
    assert result.details["hand_order_before"] == (101, 102, 103)
    assert result.details["hand_order_after"] == (103, 101, 102)


@pytest.mark.parametrize(
    "target",
    [
        (1, 0),
        (1, 1, 0),
        (0, 1, 2),
        (0, 1, 3),
        (True, 0, 2),
    ],
)
def test_dispatcher_rejects_invalid_or_noop_hand_permutations(target):
    before = _snapshot(20, [101, 102, 103])
    bridge = _RecordingBridge()

    with pytest.raises(UnsupportedInjectedAction):
        LiveMemoryInjectedActionDispatcher(
            _Observer([before]),
            bridge=bridge,
            timeout=0.1,
            poll_interval=0,
        ).dispatch(
            BalatroAction(REORDER_HAND, target=target),
            snapshot=before,
        )

    assert bridge.calls == []


def test_dispatcher_rejects_hand_reorder_outside_selecting_hand():
    before = _snapshot(30, [101, 102], phase="SHOP")

    with pytest.raises(UnsupportedInjectedAction):
        LiveMemoryInjectedActionDispatcher(
            _Observer([before]),
            bridge=_RecordingBridge(),
            timeout=0.1,
            poll_interval=0,
        ).dispatch(
            BalatroAction(REORDER_HAND, target=(1, 0)),
            snapshot=before,
        )


def test_policy_places_highest_straight_card_first_for_hanging_chad():
    cards = [BalatroCard(str(rank), "Spades") for rank in range(2, 7)]
    state = _state(cards, [HangingChadJoker()])

    decision = HandOrderPolicy().recommend(
        state,
        BalatroAction(PLAY_CARDS, cards=cards),
    )

    assert decision is not None
    assert decision.permutation == (4, 0, 1, 2, 3)
    assert decision.ordered_guaranteed_score > decision.current_guaranteed_score


def test_policy_does_not_reorder_without_order_sensitive_joker():
    two = BalatroCard("2", "Spades")
    king = BalatroCard("K", "Hearts")
    state = _state([two, king])

    assert HandOrderPolicy().recommend(
        state,
        BalatroAction(PLAY_CARDS, cards=[two, king]),
    ) is None


def test_bridge_asset_validates_full_hand_permutation():
    source = bridge_asset_path().read_text(encoding="utf-8")

    assert "local function execute_reorder_hand(payload)" in source
    assert 'return false, "hand reorder must include every card exactly once"' in source
    assert "G.hand.cards[position] = reordered[position]" in source
    assert 'elseif action == "REORDER_HAND" then' in source
    assert "hand_reorder=1" in source
