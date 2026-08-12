from types import SimpleNamespace

import pytest

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.live.external.live_memory_action_dispatcher import (
    ExternalLiveActionPostconditionError,
    LiveMemoryActionDispatcher,
    _hand_action_complete,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


def _snapshot(
    sequence,
    *,
    phase="SELECTING_HAND",
    hands=4,
    discards=4,
):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=True,
        payload={
            "round": {
                "hands_left": hands,
                "discards_left": discards,
            },
        },
    )


class _Observer:
    def __init__(self, snapshots):
        self.snapshots = list(snapshots)
        self.last = self.snapshots[-1]

    def observe(self):
        if self.snapshots:
            self.last = self.snapshots.pop(0)
        return self.last


class _HandExecutor:
    def __init__(self):
        self.calls = []

    def dispatch(self, action, state, snapshot):
        self.calls.append((action, state, snapshot))
        return (1, 2)


def _dispatcher(observer, hand_executor):
    unused = object()
    return LiveMemoryActionDispatcher(
        observer,
        mouse=object(),
        window_locator=object(),
        hand_executor=hand_executor,
        buy_executor=unused,
        buy_and_use_executor=unused,
        special_executor=unused,
        reroll_executor=unused,
        next_round_executor=unused,
        cash_out_executor=unused,
        pack_card_executor=unused,
        pack_skip_executor=unused,
        timeout=0.001,
        poll_interval=0.0,
    )


def test_play_rejects_sequence_only_change_without_hand_consumption():
    before = _snapshot(1, hands=4, discards=4)
    intermediate = _snapshot(2, hands=4, discards=4)

    assert not _hand_action_complete(before, intermediate, PLAY_CARDS)


def test_play_accepts_exactly_one_consumed_hand():
    before = _snapshot(1, hands=4, discards=4)
    after = _snapshot(2, hands=3, discards=4)

    assert _hand_action_complete(before, after, PLAY_CARDS)


def test_play_accepts_round_eval_terminal_checkpoint():
    before = _snapshot(1, hands=1, discards=0)
    after = _snapshot(2, phase="ROUND_EVAL", hands=1, discards=0)

    assert _hand_action_complete(before, after, PLAY_CARDS)


def test_discard_requires_exactly_one_consumed_discard():
    before = _snapshot(1, hands=4, discards=4)
    unchanged = _snapshot(2, hands=4, discards=4)
    after = _snapshot(3, hands=4, discards=3)

    assert not _hand_action_complete(before, unchanged, DISCARD_CARDS)
    assert _hand_action_complete(before, after, DISCARD_CARDS)


def test_dispatch_waits_through_intermediate_sequence_change_for_play():
    before = _snapshot(1, hands=4, discards=4)
    intermediate = _snapshot(2, hands=4, discards=4)
    after = _snapshot(3, hands=3, discards=4)
    observer = _Observer([intermediate, after])
    hand_executor = _HandExecutor()
    dispatcher = _dispatcher(observer, hand_executor)
    state = SimpleNamespace(phase="SELECTING_HAND")
    action = BalatroAction(PLAY_CARDS, cards=[object()])

    result = dispatcher.dispatch(action, state=state, snapshot=before)

    assert result.after is after
    assert result.details == (1, 2)
    assert len(hand_executor.calls) == 1


def test_dispatch_times_out_when_only_intermediate_state_changes():
    before = _snapshot(1, hands=4, discards=4)
    intermediate = _snapshot(2, hands=4, discards=4)
    observer = _Observer([intermediate])
    dispatcher = _dispatcher(observer, _HandExecutor())
    state = SimpleNamespace(phase="SELECTING_HAND")
    action = BalatroAction(PLAY_CARDS, cards=[object()])

    with pytest.raises(ExternalLiveActionPostconditionError, match="semantic checkpoint"):
        dispatcher.dispatch(action, state=state, snapshot=before)
