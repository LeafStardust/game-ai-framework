from games.balatro.live import (
    BalatroLiveSynchronizer,
    LiveBalatroSnapshot,
)


class FakeBridge:
    def __init__(self, snapshots):
        self.snapshots = iter(snapshots)
        self.current = None

    def is_connected(self):
        return True

    def observe(self):
        self.current = next(self.snapshots)
        return self.current

    def send(self, command):
        pass


def test_synchronizer_skips_incomplete_and_stale_snapshots():
    bridge = FakeBridge([
        LiveBalatroSnapshot(1, "1", False),
        LiveBalatroSnapshot(2, "1", True),
        LiveBalatroSnapshot(3, "1", True),
    ])
    synchronizer = BalatroLiveSynchronizer(
        bridge,
        poll_interval=0,
        timeout=1,
    )

    snapshot = synchronizer.wait_for_ready(
        after_sequence=2
    )

    assert snapshot.sequence == 3


def test_synchronizer_can_accept_new_partial_save_snapshot():
    bridge = FakeBridge([
        LiveBalatroSnapshot(4, "SELECTING_HAND", False),
        LiveBalatroSnapshot(4, "SELECTING_HAND", False),
        LiveBalatroSnapshot(5, "SELECTING_HAND", False),
    ])
    synchronizer = BalatroLiveSynchronizer(
        bridge,
        poll_interval=0,
        timeout=1,
    )
    current = LiveBalatroSnapshot(4, "SELECTING_HAND", False)

    snapshot = synchronizer.wait_for_change(
        current,
        require_complete=False,
    )

    assert snapshot.sequence == 5
    assert snapshot.state_complete is False


def test_synchronizer_filters_phases():
    bridge = FakeBridge([
        LiveBalatroSnapshot(1, "SHOP", True),
        LiveBalatroSnapshot(2, "SELECTING_HAND", True),
    ])
    synchronizer = BalatroLiveSynchronizer(
        bridge,
        poll_interval=0,
        timeout=1,
    )

    snapshot = synchronizer.wait_for_ready(
        phases={"SELECTING_HAND"}
    )

    assert snapshot.sequence == 2
    assert snapshot.phase == "SELECTING_HAND"
