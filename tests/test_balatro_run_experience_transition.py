from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from games.balatro.actions import BalatroAction
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.run_experience import (
    BalatroRunExperienceLogger,
    BalatroRunIdentity,
)
from games.balatro.live.run_experience_transition import (
    log_successful_live_transition,
)


def _snapshot(sequence: int, phase: str, *, won: bool = False) -> LiveBalatroSnapshot:
    return LiveBalatroSnapshot(
        sequence=sequence,
        phase=phase,
        state_complete=True,
        payload={
            "won": won,
            "ante_num": 1,
            "hand": {
                "cards": [
                    {
                        "value": {"rank": "A", "suit": "Spades"},
                        "ui": {"x": 12.5, "y": 3.0},
                    }
                ]
            },
        },
    )


def _decision(before: LiveBalatroSnapshot, card: object):
    state = SimpleNamespace(
        deck_name="RED",
        stake_name="WHITE",
        hand=[card],
    )
    return SimpleNamespace(
        snapshot=before,
        state=state,
        action=BalatroAction("PLAY_CARDS", cards=[card]),
        source="test hand policy",
        notes=("mode=TEST",),
    )


def _contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def test_successful_transitions_resume_sequence_and_write_terminal_summary(tmp_path):
    card = object()
    first = _decision(_snapshot(1, "SELECTING_HAND"), card)
    first_result = SimpleNamespace(after=_snapshot(2, "ROUND_EVAL"))

    first_logger = log_successful_live_transition(
        first,
        first_result,
        run_id="live-run-001",
        directory=tmp_path,
    )

    assert first_logger.sequence == 4
    assert first_logger.summary_path.exists() is False

    second = _decision(_snapshot(2, "SELECTING_HAND"), card)
    terminal = SimpleNamespace(after=_snapshot(3, "GAME_OVER", won=False))
    second_logger = log_successful_live_transition(
        second,
        terminal,
        run_id="live-run-001",
        directory=tmp_path,
    )

    rows = [
        json.loads(line)
        for line in second_logger.path.read_text(encoding="utf-8").splitlines()
    ]
    assert [row["sequence"] for row in rows] == list(range(1, 9))
    assert [row["event"] for row in rows] == [
        "run_started",
        "observation",
        "decision",
        "action_result",
        "observation",
        "decision",
        "action_result",
        "run_finished",
    ]
    assert rows[2]["data"]["action"]["indices"] == [0]
    assert _contains_key(rows, "ui") is False

    summary = json.loads(second_logger.summary_path.read_text(encoding="utf-8"))
    assert summary["schema"] == "balatro-run-summary-v1"
    assert summary["won"] is False
    assert summary["reason"] == "game_over"
    assert summary["event_count"] == 8
    assert summary["last_sequence"] == 8
    assert summary["event_counts"]["run_started"] == 1
    assert summary["event_counts"]["run_finished"] == 1
    assert summary["final_state"]["phase"] == "GAME_OVER"


def test_resumed_logger_rejects_identity_mismatch(tmp_path):
    run = BalatroRunIdentity(
        run_id="same-id",
        deck="RED",
        stake="WHITE",
        playbook="red-white",
        playbook_version="0.8",
    )
    logger = BalatroRunExperienceLogger(run, directory=tmp_path)
    logger.run_started(state={"phase": "BLIND_SELECT"})

    incompatible = BalatroRunIdentity(
        run_id="same-id",
        deck="RED",
        stake="BLACK",
        playbook="red-white",
        playbook_version="0.8",
    )
    with pytest.raises(ValueError, match="identity mismatch"):
        BalatroRunExperienceLogger(incompatible, directory=tmp_path)


def test_run_id_cannot_be_empty(tmp_path):
    card = object()
    decision = _decision(_snapshot(1, "SELECTING_HAND"), card)
    result = SimpleNamespace(after=_snapshot(2, "ROUND_EVAL"))

    with pytest.raises(ValueError, match="run_id cannot be empty"):
        log_successful_live_transition(
            decision,
            result,
            run_id="   ",
            directory=tmp_path,
        )
