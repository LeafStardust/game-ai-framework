from __future__ import annotations

from types import SimpleNamespace

from games.balatro.actions import BalatroAction
from games.balatro.live.injected.hand_dispatcher import (
    InjectedHandActionPostconditionError,
)
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.live_memory_autonomous_loop_injected import (
    LiveMemoryInjectedAutonomousLoop,
)
from games.balatro.live.runtime.live_memory_autonomous_step_injected import (
    AutonomousStepDecision,
    LiveMemoryInjectedSingleStepRunner,
)


def _snapshot(sequence: int) -> LiveBalatroSnapshot:
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase="SELECTING_HAND",
        state_complete=True,
        payload={
            "deck": "RED",
            "stake": "WHITE",
            "won": False,
            "round": {"hands_left": 2, "discards_left": 0},
        },
    )


class _StableObserver:
    def __init__(self):
        self.sequence = 1

    def observe(self):
        return _snapshot(self.sequence)


class _Recommendation:
    def __init__(self, consumable):
        self.consumable = consumable
        self.should_use = True
        self.target = None
        self.rationale = ()

    def to_action(self):
        return BalatroAction("USE_CONSUMABLE", target=self.consumable)


class _TimingPolicy:
    def __init__(self, consumables):
        self.consumables = tuple(consumables)

    def recommend_inventory(self, state):
        del state
        return tuple(_Recommendation(card) for card in self.consumables)


def test_quarantined_consumable_is_skipped_on_replan():
    failed = SimpleNamespace(live_id=101, name="The Lovers")
    fallback = SimpleNamespace(live_id=102, name="Temperance")
    runner = LiveMemoryInjectedSingleStepRunner(
        _StableObserver(),
        bridge=SimpleNamespace(),
        dispatcher=SimpleNamespace(),
        consumable_timing_policy=_TimingPolicy((failed, fallback)),
    )
    failed_decision = AutonomousStepDecision(
        _snapshot(1),
        SimpleNamespace(),
        BalatroAction("USE_CONSUMABLE", target=failed),
        "B6 consumable timing policy",
    )

    assert runner.quarantine_failed_consumable(failed_decision) is True

    action, _ = runner._recommend_consumable_use(
        SimpleNamespace(consumables=[failed, fallback], phase="SELECTING_HAND")
    )
    assert action.target is fallback


class _RecoveringRunner:
    def __init__(self):
        self.observer = _StableObserver()
        self.failed = SimpleNamespace(live_id=201, name="The Lovers")
        self.quarantined = set()
        self.decisions = 0
        self.last_observation_seconds = 0.0
        self.last_translation_seconds = 0.0
        self.last_policy_seconds = 0.0

    def decide(self):
        self.decisions += 1
        if not self.quarantined:
            return AutonomousStepDecision(
                _snapshot(1),
                SimpleNamespace(),
                BalatroAction("USE_CONSUMABLE", target=self.failed),
                "B6 consumable timing policy",
            )
        return AutonomousStepDecision(
            _snapshot(1),
            SimpleNamespace(),
            BalatroAction("PLAY_CARDS"),
            "D1 hand-action policy",
        )

    def quarantine_failed_consumable(self, decision):
        live_id = getattr(decision.action.target, "live_id", None)
        if live_id is None:
            return False
        self.quarantined.add(live_id)
        return True

    def execute(self, decision):
        if decision.action.name == "USE_CONSUMABLE":
            raise InjectedHandActionPostconditionError(
                "timed out verifying injected consumable use; "
                "phase=SELECTING_HAND, sequence=1350"
            )
        after = _snapshot(2)
        return SimpleNamespace(after=after), {"achievement_gate": "ENABLED"}


def test_loop_replans_after_consumable_postcondition_timeout():
    runner = _RecoveringRunner()
    loop = LiveMemoryInjectedAutonomousLoop(
        runner,
        max_steps=1,
        stability_interval_seconds=0.0,
        stability_timeout_seconds=0.01,
    )

    result = loop.execute(expected_start_phase="SELECTING_HAND")

    assert len(result.steps) == 1
    assert result.steps[0].decision.action.name == "PLAY_CARDS"
    assert result.steps[0].stale_replans == 1
    assert runner.quarantined == {201}
    assert result.stop_reason == "max steps reached"
