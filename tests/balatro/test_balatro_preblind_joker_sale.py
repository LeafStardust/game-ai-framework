from __future__ import annotations

from games.balatro.actions import BalatroAction, SELL_JOKER
from games.balatro.live.injected import LiveMemoryInjectedActionDispatcher
from games.balatro.live.protocol import LiveBalatroSnapshot


class _Observer:
    def __init__(self, snapshots):
        self._snapshots = iter(snapshots)

    def observe(self):
        return next(self._snapshots)


class _Bridge:
    def __init__(self):
        self.sold = []

    def sell_joker(self, index):
        self.sold.append(index)


def _snapshot(sequence, jokers, *, phase="BLIND_SELECT"):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=True,
        payload={"jokers": {"cards": jokers}},
    )


def test_sell_joker_is_legal_during_settled_blind_select_cleanup():
    popcorn = {"live_id": 101, "label": "Popcorn", "public_state": {"mult": 4.0}}
    blue = {"live_id": 102, "label": "Blue Joker"}
    before = _snapshot(10, [popcorn, blue])
    after = _snapshot(11, [blue])
    bridge = _Bridge()
    dispatcher = LiveMemoryInjectedActionDispatcher(
        _Observer([after]),
        bridge=bridge,
        timeout=0.0,
        poll_interval=0.0,
    )

    result = dispatcher.dispatch(
        BalatroAction(SELL_JOKER, target={"area_index": 0}),
        snapshot=before,
    )

    assert bridge.sold == [0]
    assert result.before == before
    assert result.after == after
    assert result.details["sale_context"] == "BLIND_SELECT"


def test_preblind_sale_patch_does_not_capture_other_phases():
    before = _snapshot(20, [{"live_id": 201, "label": "Popcorn"}], phase="SELECTING_HAND")
    dispatcher = LiveMemoryInjectedActionDispatcher(
        _Observer([]),
        bridge=_Bridge(),
        timeout=0.0,
        poll_interval=0.0,
    )

    try:
        dispatcher.dispatch(
            BalatroAction(SELL_JOKER, target={"area_index": 0}),
            snapshot=before,
        )
    except Exception as exc:
        assert "SELL_JOKER requires" in str(exc)
    else:
        raise AssertionError("non-Verdant SELECTING_HAND sale should remain illegal")
