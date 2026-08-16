from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from games.balatro.actions import (
    END_ROUND,
    END_SHOP,
    PLAY_CARDS,
    SELECT_BLIND,
    SELECT_PACK_CARD,
    BalatroAction,
)
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.agent_control import BalatroAgentControl
from games.balatro.live.runtime.balatro_agent_supervisor import BalatroAgentSupervisor
from games.balatro.live.runtime.live_memory_autonomous_loop_injected import (
    LiveMemoryInjectedAutonomousLoop,
)
from games.balatro.live.runtime.live_memory_autonomous_step_injected import (
    AutonomousStepDecision,
    LiveMemoryInjectedSingleStepRunner,
)


class _NoConsumables:
    def recommend_inventory(self, _state):
        return ()


class _Observer:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    def observe(self):
        return self.snapshot


class _Translator:
    def translate(self, snapshot):
        return SimpleNamespace(
            phase=snapshot.phase,
            hand=[],
            consumables=[],
        )


@pytest.mark.parametrize(
    ("phase", "expected_action", "expected_source"),
    [
        ("BLIND_SELECT", SELECT_BLIND, "D13 blind play-vs-skip policy"),
        ("SELECTING_HAND", PLAY_CARDS, "D1 hand-action policy"),
        ("ROUND_EVAL", END_ROUND, "deterministic round-flow policy"),
        ("SHOP", END_SHOP, "shop policy"),
        ("BUFFOON_PACK", SELECT_PACK_CARD, "pack policy"),
        ("STANDARD_PACK", SELECT_PACK_CARD, "pack policy"),
        ("PLANET_PACK", SELECT_PACK_CARD, "pack policy"),
        ("TAROT_PACK", SELECT_PACK_CARD, "pack policy"),
        ("SPECTRAL_PACK", SELECT_PACK_CARD, "pack policy"),
    ],
)
def test_all_canonical_action_driving_phases_route_to_production_policy(
    phase,
    expected_action,
    expected_source,
):
    snapshot = LiveBalatroSnapshot(
        sequence=1,
        phase=phase,
        state_complete=True,
        payload={"marker": 1},
    )
    play_action = BalatroAction(PLAY_CARDS)
    shop_action = BalatroAction(END_SHOP)
    pack_action = BalatroAction(SELECT_PACK_CARD, target={"area_index": 0})

    runner = LiveMemoryInjectedSingleStepRunner(
        _Observer(snapshot),
        translator=_Translator(),
        consumable_timing_policy=_NoConsumables(),
        hand_recommender=lambda _state, _snapshot: (play_action, ("test",)),
        shop_recommender=lambda _state, _snapshot: (shop_action, ("test",)),
        pack_recommender=lambda _state, _snapshot: (
            pack_action,
            ("test",),
            (),
        ),
    )

    decision = runner.decide()

    assert decision.action.name == expected_action
    assert decision.source == expected_source


class _LongRunRunner:
    def __init__(self, action_count: int):
        self.action_count = int(action_count)
        self.index = 0

    def decide(self):
        snapshot = LiveBalatroSnapshot(
            sequence=self.index + 1,
            phase="SELECTING_HAND",
            state_complete=True,
            payload={"step": self.index},
        )
        return AutonomousStepDecision(
            snapshot=snapshot,
            state=SimpleNamespace(hand=()),
            action=BalatroAction(PLAY_CARDS),
            source="test D1",
            notes=(),
        )

    def execute(self, decision):
        assert decision.snapshot.sequence == self.index + 1
        self.index += 1
        terminal = self.index >= self.action_count
        after = LiveBalatroSnapshot(
            sequence=self.index + 1,
            phase="GAME_OVER" if terminal else "SELECTING_HAND",
            state_complete=True,
            payload={"step": self.index, "won": terminal},
        )
        return SimpleNamespace(after=after), {
            "bridge": "1",
            "achievement_gate": "ENABLED",
        }


def test_unbounded_production_loop_has_no_hidden_gameplay_step_cap():
    runner = _LongRunRunner(128)
    loop = LiveMemoryInjectedAutonomousLoop(runner, max_steps=None)

    result = loop.execute(expected_start_phase="SELECTING_HAND")

    assert len(result.steps) == 128
    assert runner.index == 128
    assert result.stop_reason == "game over (won)"
    assert result.steps[-1].after_phase == "GAME_OVER"


class _AttemptObserver:
    def __init__(self, *, won: bool):
        self.won = bool(won)
        self.finished = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None

    def observe(self):
        if not self.finished:
            return LiveBalatroSnapshot(
                sequence=1,
                phase="SELECTING_HAND",
                state_complete=True,
                payload={
                    "deck": "RED",
                    "stake": "WHITE",
                    "won": False,
                    "hand": {"cards": []},
                },
            )
        return LiveBalatroSnapshot(
            sequence=2,
            phase="GAME_OVER",
            state_complete=True,
            payload={
                "deck": "RED",
                "stake": "WHITE",
                "won": self.won,
                "hand": {"cards": []},
            },
        )


class _AttemptRunner:
    def __init__(self, observer):
        self.observer = observer
        self.last_observation_seconds = 0.0
        self.last_translation_seconds = 0.0
        self.last_policy_seconds = 0.0

    def decide(self):
        snapshot = self.observer.observe()
        return AutonomousStepDecision(
            snapshot=snapshot,
            state=SimpleNamespace(
                deck_name="RED",
                stake_name="WHITE",
                hand=(),
            ),
            action=BalatroAction(PLAY_CARDS),
            source="test D1",
            notes=("mode=TEST",),
        )

    def execute(self, decision):
        assert decision.snapshot.phase == "SELECTING_HAND"
        self.observer.finished = True
        return SimpleNamespace(after=self.observer.observe()), {
            "bridge": "1",
            "achievement_gate": "ENABLED",
        }


class _AttemptFactory:
    def __init__(self, outcomes):
        self.outcomes = tuple(bool(value) for value in outcomes)
        self.index = 0
        self.restart_calls = []

    def observer(self):
        return _AttemptObserver(won=self.outcomes[self.index])

    def restart(self, _runner, deck, stake):
        self.restart_calls.append((deck, stake))
        self.index += 1


def test_supervisor_continues_across_multiple_consecutive_losses(tmp_path):
    factory = _AttemptFactory([False, False, True])
    control = BalatroAgentControl(tmp_path / "control")
    supervisor = BalatroAgentSupervisor(
        control=control,
        observer_factory=factory.observer,
        runner_factory=_AttemptRunner,
        restart_run=factory.restart,
        run_log_directory=tmp_path / "runs",
        session_directory=tmp_path / "sessions",
        session_id="multi-loss-release",
        startup_stability_interval_seconds=0.0,
    )

    result = supervisor.run()

    assert result.won is True
    assert [attempt.outcome for attempt in result.attempts] == ["LOSS", "LOSS", "WIN"]
    assert [attempt.run_id for attempt in result.attempts] == [
        "multi-loss-release-attempt-001",
        "multi-loss-release-attempt-002",
        "multi-loss-release-attempt-003",
    ]
    assert factory.restart_calls == [("RED", "WHITE"), ("RED", "WHITE")]
    assert control.read_status()["state"] == "OFF"

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert summary["attempt_count"] == 3
    assert summary["loss_count"] == 2
    assert summary["won"] is True

    for attempt in result.attempts:
        assert (tmp_path / "runs" / f"{attempt.run_id}.jsonl").exists()
        assert (tmp_path / "runs" / f"{attempt.run_id}.summary.json").exists()
