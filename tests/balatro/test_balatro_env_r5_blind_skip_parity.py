from copy import deepcopy

import pytest

from games.balatro.actions import SKIP_BLIND
from games.balatro.env.actions import EnvAction
from games.balatro.env.strategic_evidence import build_public_strategic_transition_evidence
from games.balatro.live.blind_skip_parity_capture import (
    LiveBlindSkipParityRecorder,
    blind_skip_parity_checkpoint_from_payload,
    blind_skip_parity_checkpoint_to_payload,
)
from games.balatro.live.blind_skip_parity_checkpoint import (
    LiveBlindSkipParityCheckpoint,
    LiveBlindSkipParityCheckpointError,
    LiveBlindSkipProgression,
    capture_live_blind_skip_parity_checkpoint,
    compare_live_blind_skip_replay,
    headless_blind_skip_run_from_live_checkpoint,
)
from games.balatro.live.parity_capture import successful_skip_blind_evidence_from_run_rows
from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.luajit_memory import LuaValue
from games.balatro.live.translator import DefaultBalatroStateTranslator


def _snapshot(sequence, *, blind_type="SMALL", tag="tag_economy", money=17):
    requirement = 800 if blind_type == "SMALL" else 1_200
    return LiveBalatroSnapshot(
        sequence,
        "BLIND_SELECT",
        True,
        {
            "deck": "RED",
            "stake": "WHITE",
            "ante_num": 2,
            "round_num": 1,
            "money": money,
            "score": 0,
            "round": {"hands_left": 4, "discards_left": 3, "chips": requirement},
            "hand": {"limit": 8, "cards": []},
            "cards": {"cards": []},
            "jokers": {"limit": 5, "count": 0, "cards": []},
            "consumables": {"limit": 2, "cards": []},
            "vouchers_observed": True,
            "vouchers": [],
            "blinds": {
                blind_type.lower(): {
                    "type": blind_type,
                    "status": "SELECT",
                    "score": requirement,
                    "reward": 3 if blind_type == "SMALL" else 4,
                    "tag": tag,
                }
            },
        },
    )


def _progression(*, after=False, big_tag="tag_meteor"):
    return LiveBlindSkipProgression(
        small_status="Skipped" if after else "Select",
        big_status="Select" if after else "Upcoming",
        boss_status="Upcoming",
        blind_on_deck="Big" if after else "Small",
        blind_ante=2,
        small_tag="tag_economy",
        big_tag=big_tag,
    )


def _checkpoint(*, after=False, skips=3, big_tag="tag_meteor"):
    return LiveBlindSkipParityCheckpoint(
        public_snapshot=(
            _snapshot(2, blind_type="BIG", tag=big_tag, money=34)
            if after
            else _snapshot(1)
        ),
        progression=_progression(after=after, big_tag=big_tag),
        active_tag_count=0,
        skips=skips,
    )


def _log_state(snapshot):
    return {
        "sequence": snapshot.sequence,
        "phase": snapshot.phase,
        "state_complete": snapshot.state_complete,
        "payload": deepcopy(snapshot.payload),
    }


def test_env_r5_economy_skip_replays_exact_public_and_private_transition():
    before = _checkpoint()
    after = _checkpoint(after=True, skips=4)
    before_run = headless_blind_skip_run_from_live_checkpoint(before)
    live_after = DefaultBalatroStateTranslator().translate(after.public_snapshot)
    live_evidence = build_public_strategic_transition_evidence(
        before_run.public,
        EnvAction.from_alias("SKIP_BLIND"),
        live_after,
    )

    comparison = compare_live_blind_skip_replay(before, after, live_evidence)

    assert comparison.matches
    assert comparison.differences == ()
    assert comparison.simulator_evidence.after.money == 34
    assert comparison.simulator_evidence.after.blind_score == 1_200
    assert comparison.simulator_evidence.after.blind.requirement == 1_200
    assert comparison.simulator_evidence.after.blind.reward == 4
    assert comparison.simulator_evidence.after.blind.tag_key == "tag_meteor"


def test_env_r5_economy_skip_reports_private_and_public_mismatch():
    before = _checkpoint()
    after = _checkpoint(after=True, skips=3, big_tag="tag_buffoon")
    before_run = headless_blind_skip_run_from_live_checkpoint(before)
    live_after = DefaultBalatroStateTranslator().translate(after.public_snapshot)
    live_evidence = build_public_strategic_transition_evidence(
        before_run.public,
        EnvAction.from_alias("SKIP_BLIND"),
        live_after,
    )

    comparison = compare_live_blind_skip_replay(before, after, live_evidence)

    assert comparison.matches is False
    assert comparison.differences == (
        "public.after",
        "private.skips.after",
        "private.blind_progression.after",
    )


def test_env_r5_blind_skip_restore_fails_closed_without_private_authority():
    missing_tag = LiveBlindSkipParityCheckpoint(
        _snapshot(1), _progression(big_tag=""), 0, 0
    )
    with pytest.raises(LiveBlindSkipParityCheckpointError, match="cannot restore"):
        headless_blind_skip_run_from_live_checkpoint(missing_tag)

    active_tag = LiveBlindSkipParityCheckpoint(_snapshot(1), _progression(), 1, 0)
    with pytest.raises(LiveBlindSkipParityCheckpointError, match="active Tags"):
        headless_blind_skip_run_from_live_checkpoint(active_tag)


def test_env_r5_skip_blind_log_mapping_is_parameterless_and_fail_closed():
    before = _snapshot(10)
    after = _snapshot(11, blind_type="BIG", tag="tag_meteor", money=34)
    action = {"name": SKIP_BLIND}
    rows = [
        {"event": "observation", "data": {"state": _log_state(before)}},
        {"event": "decision", "data": {"action": action}},
        {"event": "action_result", "data": {
            "action": action, "success": True, "state": _log_state(after)
        }},
    ]

    evidence = successful_skip_blind_evidence_from_run_rows(rows)

    assert evidence[0].action.alias == "SKIP_BLIND"
    assert evidence[0].action.params == ()
    rows[1]["data"]["action"] = {"name": SKIP_BLIND, "target": {}}
    rows[2]["data"]["action"] = rows[1]["data"]["action"]
    with pytest.raises(ValueError, match="must not contain parameters"):
        successful_skip_blind_evidence_from_run_rows(rows)


def _lua(kind, value):
    return LuaValue(kind=kind, value=value, raw=0)


class _Decoder:
    def __init__(self, *, big_tag="tag_meteor"):
        self.tables = {
            100: {
                "round_resets": _lua("table", 200),
                "blind_on_deck": _lua("string", "Small"),
                "skips": _lua("number", 2.0),
                "tags": _lua("table", 500),
            },
            200: {
                "blind_ante": _lua("number", 2.0),
                "blind_states": _lua("table", 300),
                "blind_tags": _lua("table", 400),
            },
            300: {
                "Small": _lua("string", "Select"),
                "Big": _lua("string", "Upcoming"),
                "Boss": _lua("string", "Upcoming"),
            },
            400: {
                "Small": _lua("string", "tag_economy"),
                "Big": _lua("string", big_tag),
            },
        }

    def string_fields(self, address):
        return dict(self.tables[address])

    def array_items(self, address):
        assert address == 500
        return []


class _Observer:
    def __init__(self, *, big_tag="tag_meteor"):
        self.snapshot = _snapshot(1)
        self.decoder = _Decoder(big_tag=big_tag)

    def observe(self):
        return deepcopy(self.snapshot)

    def _root(self):
        return self.decoder, 0, {"GAME": _lua("table", 100)}


def test_env_r5_blind_skip_capture_reads_exact_retained_progression():
    checkpoint = capture_live_blind_skip_parity_checkpoint(_Observer())

    assert checkpoint.progression == _progression()
    assert checkpoint.skips == 2
    assert checkpoint.active_tag_count == 0


def test_env_r5_blind_skip_capture_rejects_missing_next_tag_authority():
    with pytest.raises(LiveBlindSkipParityCheckpointError, match="cannot be empty"):
        capture_live_blind_skip_parity_checkpoint(_Observer(big_tag=""))


def test_env_r5_blind_skip_checkpoint_payload_roundtrip():
    checkpoint = _checkpoint()
    assert blind_skip_parity_checkpoint_from_payload(
        blind_skip_parity_checkpoint_to_payload(checkpoint)
    ) == checkpoint


def test_env_r5_blind_skip_recorder_rejects_unsupported_tag_before_dispatch(tmp_path):
    observer = _Observer()
    observer.snapshot = _snapshot(1, tag="tag_double")
    decision = type("Decision", (), {
        "snapshot": observer.snapshot,
        "action": type("Action", (), {"name": SKIP_BLIND, "cards": (), "target": None})(),
    })()
    recorder = LiveBlindSkipParityRecorder("attempt-001", observer, directory=tmp_path)

    with pytest.raises(RuntimeError, match="exact Economy-Tag skip subset"):
        recorder.capture_before(decision)
