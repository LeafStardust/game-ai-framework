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


class _PreparedBuildIntent:
    def __init__(self):
        self.payload = {
            "transition": "INITIAL",
            "changed_fields": ["jokers"],
            "profile": {"jokers": ["JokerJoker"]},
            "intent": {
                "mode": "PIVOTABLE",
                "locked": False,
                "lock_ante": None,
                "strengths": {"pair": 1.0},
            },
            "detected_synergies": [],
        }
        self.committed = False

    def commit(self):
        self.committed = True


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
    assert "build_rationale" not in rows[2]["data"]["rationale"]
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


def test_prepared_build_intent_is_written_before_decision_then_committed(tmp_path):
    card = object()
    decision = _decision(_snapshot(1, "SELECTING_HAND"), card)
    prepared = _PreparedBuildIntent()
    decision.build_intent = prepared
    result = SimpleNamespace(after=_snapshot(2, "ROUND_EVAL"))

    logger = log_successful_live_transition(
        decision,
        result,
        run_id="build-run-001",
        directory=tmp_path,
    )

    rows = [
        json.loads(line)
        for line in logger.path.read_text(encoding="utf-8").splitlines()
    ]
    assert [row["event"] for row in rows] == [
        "run_started",
        "observation",
        "build_intent",
        "decision",
        "action_result",
    ]
    assert rows[2]["data"]["transition"] == "INITIAL"
    assert rows[2]["data"]["profile"]["jokers"] == ["JokerJoker"]
    assert prepared.committed is True


def test_chosen_purchase_logs_only_policy_supplied_build_causal_signals(tmp_path):
    state = SimpleNamespace(
        deck_name="RED",
        stake_name="WHITE",
        hand=[],
    )
    target = SimpleNamespace(name="Candidate Joker", price=5)
    prepared = _PreparedBuildIntent()
    decision = SimpleNamespace(
        snapshot=_snapshot(10, "SHOP"),
        state=state,
        action=BalatroAction("BUY_JOKER", target=target),
        source="shop policy",
        notes=(
            "policy_score=8.000000",
            "B3 interaction=2.500",
            "Candidate Joker creates rank:A -> held:rank:A; enables requirement for ExistingJoker (+1.250)",
            "playstyle fit=1.000 value=2.000 mode=PIVOTABLE",
            "price penalty=5.000",
        ),
        build_intent=prepared,
    )
    result = SimpleNamespace(after=_snapshot(11, "SHOP"))

    logger = log_successful_live_transition(
        decision,
        result,
        run_id="build-rationale-001",
        directory=tmp_path,
    )

    rows = [
        json.loads(line)
        for line in logger.path.read_text(encoding="utf-8").splitlines()
    ]
    decision_row = next(row for row in rows if row["event"] == "decision")
    rationale = decision_row["data"]["rationale"]["build_rationale"]

    assert rationale["action_family"] == "PURCHASE"
    assert rationale["decision_source"] == "shop policy"
    assert rationale["intent_before"]["mode"] == "PIVOTABLE"
    assert rationale["intent_before"]["strengths"] == {"pair": 1.0}
    assert [signal["kind"] for signal in rationale["signals"]] == [
        "B3",
        "INTERACTION",
        "PLAYSTYLE",
    ]
    assert all(
        signal["text"] not in {"policy_score=8.000000", "price penalty=5.000"}
        for signal in rationale["signals"]
    )


def test_targeted_pack_choice_logs_b6_and_d9_rationale_without_recomputing(tmp_path):
    cards = [object(), object()]
    state = SimpleNamespace(
        deck_name="RED",
        stake_name="WHITE",
        hand=cards,
    )
    decision = SimpleNamespace(
        snapshot=_snapshot(20, "TAROT_PACK"),
        state=state,
        action=BalatroAction(
            "SELECT_PACK_CARD",
            cards=cards,
            target=SimpleNamespace(label="The Sun", area_index=1),
        ),
        source="pack policy",
        notes=(
            "policy_score=4.250000",
            "B6 pack target gain=2.000",
            "D9 playstyle fit=0.500 value=1.125 mode=PIVOTABLE",
            "target_indices=(0, 1)",
        ),
    )
    result = SimpleNamespace(after=_snapshot(21, "SHOP"))

    logger = log_successful_live_transition(
        decision,
        result,
        run_id="build-rationale-002",
        directory=tmp_path,
    )

    rows = [
        json.loads(line)
        for line in logger.path.read_text(encoding="utf-8").splitlines()
    ]
    decision_row = next(row for row in rows if row["event"] == "decision")
    rationale = decision_row["data"]["rationale"]["build_rationale"]

    assert rationale["action_family"] == "PACK_CHOICE"
    assert [signal["kind"] for signal in rationale["signals"]] == ["B6", "D9"]
    assert decision_row["data"]["action"]["indices"] == [0, 1]
    assert decision_row["data"]["action"]["target"]["label"] == "The Sun"


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
