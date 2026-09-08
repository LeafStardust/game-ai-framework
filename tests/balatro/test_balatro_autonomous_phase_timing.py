from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.live.external.live_memory_autonomous_step_injected import (
    LiveMemoryInjectedSingleStepRunner,
)
from games.balatro.live.protocol import LiveBalatroSnapshot


class _Observer:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def observe(self):
        return self.snapshot


class _Translator:
    def __init__(self, state):
        self.state = state

    def translate(self, snapshot):
        assert snapshot.phase == self.state.phase
        return self.state


def test_autonomous_runner_records_observation_translation_and_policy_timing():
    card = object()
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={"marker": 1},
    )
    state = SimpleNamespace(phase="SELECTING_HAND", hand=[card])
    action = BalatroAction(PLAY_CARDS, cards=[card])
    runner = LiveMemoryInjectedSingleStepRunner(
        _Observer(snapshot),
        translator=_Translator(state),
        bridge=object(),
        dispatcher=object(),
        hand_recommender=lambda current, current_snapshot: (action, ()),
    )

    decision = runner.decide()

    assert decision.action is action
    assert runner.last_observation_seconds >= 0.0
    assert runner.last_translation_seconds >= 0.0
    assert runner.last_policy_seconds >= 0.0
