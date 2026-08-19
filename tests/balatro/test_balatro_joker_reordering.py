import pytest

from games.balatro.actions import REORDER_JOKERS, BalatroAction
from games.balatro.live.injected.action_dispatcher import (
    LiveMemoryInjectedActionDispatcher,
    UnsupportedInjectedAction,
)
from games.balatro.live.injected.bridge import FirstPartyBalatroBridge
from games.balatro.live.injected.install import bridge_asset_path
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


def _snapshot(sequence, live_ids, *, phase="SELECTING_HAND", complete=True):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=complete,
        payload={
            "jokers": {
                "count": len(live_ids),
                "cards": [
                    {"live_id": live_id, "center": f"j_{live_id}"}
                    for live_id in live_ids
                ],
            }
        },
    )


def test_bridge_client_encodes_joker_permutation():
    bridge = _RecordingBridge()

    bridge.reorder_jokers((2, 0, 1))

    assert bridge.calls == [("REORDER_JOKERS", (2, 0, 1))]


def test_dispatcher_waits_for_exact_authoritative_joker_order():
    before = _snapshot(10, [101, 102, 103])
    moved_but_not_observed = _snapshot(11, [101, 102, 103])
    settled = _snapshot(12, [103, 101, 102])
    observer = _Observer([moved_but_not_observed, settled])
    bridge = _RecordingBridge()
    action = BalatroAction(REORDER_JOKERS, target=(2, 0, 1))

    result = LiveMemoryInjectedActionDispatcher(
        observer,
        bridge=bridge,
        timeout=0.1,
        poll_interval=0,
    ).dispatch(action, snapshot=before)

    assert bridge.calls == [("REORDER_JOKERS", (2, 0, 1))]
    assert observer.calls == 2
    assert result.after is settled
    assert result.details["permutation"] == (2, 0, 1)
    assert result.details["joker_order_before"] == (101, 102, 103)
    assert result.details["joker_order_after"] == (103, 101, 102)


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
def test_dispatcher_rejects_invalid_or_noop_joker_permutations(target):
    before = _snapshot(20, [101, 102, 103])
    bridge = _RecordingBridge()

    with pytest.raises(UnsupportedInjectedAction):
        LiveMemoryInjectedActionDispatcher(
            _Observer([before]),
            bridge=bridge,
            timeout=0.1,
            poll_interval=0,
        ).dispatch(
            BalatroAction(REORDER_JOKERS, target=target),
            snapshot=before,
        )

    assert bridge.calls == []


def test_dispatcher_rejects_joker_reorder_outside_stable_phases():
    before = _snapshot(30, [101, 102], phase="ROUND_EVAL")
    bridge = _RecordingBridge()

    with pytest.raises(UnsupportedInjectedAction):
        LiveMemoryInjectedActionDispatcher(
            _Observer([before]),
            bridge=bridge,
            timeout=0.1,
            poll_interval=0,
        ).dispatch(
            BalatroAction(REORDER_JOKERS, target=(1, 0)),
            snapshot=before,
        )

    assert bridge.calls == []


def test_bridge_asset_validates_full_joker_permutation():
    source = bridge_asset_path().read_text(encoding="utf-8")

    assert "local function execute_reorder_jokers(payload)" in source
    assert 'if #indices ~= count then' in source
    assert 'return false, "joker reorder must include every joker exactly once"' in source
    assert "G.jokers.cards[position] = reordered[position]" in source
    assert 'elseif action == "REORDER_JOKERS" then' in source
