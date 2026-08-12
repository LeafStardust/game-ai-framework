from types import SimpleNamespace

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.live.external.live_memory_autonomous_loop_injected import (
    LiveMemoryInjectedAutonomousLoop,
)
from games.balatro.live.external.live_memory_autonomous_step_injected import (
    AutonomousStepDecision,
)
from games.balatro.live.injected.hand_dispatcher import _hand_action_complete
from games.balatro.live.protocol import LiveBalatroSnapshot


def _snapshot(sequence: int, phase: str, *, won: bool = False):
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=True,
        payload={
            "won": won,
            "round": {"hands_left": 0, "discards_left": 0},
        },
    )


def test_played_hand_accepts_game_over_as_terminal_postcondition():
    before = LiveBalatroSnapshot(
        sequence=10,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={"round": {"hands_left": 1, "discards_left": 0}},
    )
    after = _snapshot(11, "GAME_OVER", won=False)

    assert _hand_action_complete(before, after, PLAY_CARDS) is True


class _TerminalRunner:
    def __init__(self):
        self.decide_calls = 0
        self.execute_calls = 0
        self.last_observation_seconds = 0.01
        self.last_translation_seconds = 0.0
        self.last_policy_seconds = 0.02

    def decide(self):
        self.decide_calls += 1
        before = LiveBalatroSnapshot(
            sequence=1,
            phase="SELECTING_HAND",
            state_complete=True,
            payload={
                "won": False,
                "round": {"hands_left": 1, "discards_left": 0},
            },
        )
        return AutonomousStepDecision(
            snapshot=before,
            state=SimpleNamespace(hand=()),
            action=BalatroAction(PLAY_CARDS),
            source="test policy",
        )

    def execute(self, decision):
        self.execute_calls += 1
        assert decision.snapshot.phase == "SELECTING_HAND"
        return (
            SimpleNamespace(after=_snapshot(2, "GAME_OVER", won=False)),
            {"bridge": "1", "achievement_gate": "ENABLED"},
        )


def test_autonomous_loop_records_final_action_and_stops_on_game_over():
    runner = _TerminalRunner()
    loop = LiveMemoryInjectedAutonomousLoop(runner, max_steps=10)

    run = loop.execute(expected_start_phase="SELECTING_HAND")

    assert len(run.steps) == 1
    assert run.steps[0].after_phase == "GAME_OVER"
    assert run.steps[0].after_sequence == 2
    assert run.stop_reason == "game over (lost)"
    assert runner.decide_calls == 1
    assert runner.execute_calls == 1
