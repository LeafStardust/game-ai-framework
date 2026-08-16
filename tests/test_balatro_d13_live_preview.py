from types import SimpleNamespace

from games.balatro.live.protocol import LiveBalatroSnapshot
from games.balatro.live.runtime.blind_skip_diagnostic import (
    collect_d13_preview,
    d13_preview_payload,
)


class _Observer:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None


class _Runner:
    def __init__(self, decision):
        self.decision = decision
        self.execute_called = False

    def decide(self):
        return self.decision

    def execute(self, decision):
        self.execute_called = True
        raise AssertionError("read-only D13 preview must never execute gameplay")


def _decision(*, phase="BLIND_SELECT", source="D13 contextual blind play-vs-skip policy"):
    snapshot = LiveBalatroSnapshot(
        sequence=17,
        phase=phase,
        state_complete=True,
        payload={
            "deck": "RED",
            "stake": "WHITE",
            "ante_num": 3,
            "money": 11,
            "blind": {
                "type": "BIG",
                "tag": "tag_negative",
            },
        },
    )
    return SimpleNamespace(
        snapshot=snapshot,
        state=SimpleNamespace(
            deck_name="RED",
            stake_name="WHITE",
            ante=3,
            money=11,
        ),
        action=SimpleNamespace(name="SKIP_BLIND"),
        source=source,
        notes=("skip_margin=3.500", "skip_threshold=2.000"),
        decision_diagnostics={
            "layer": "D13",
            "selected": {
                "margin": 3.5,
                "threshold": 2.0,
            },
        },
    )


def test_d13_preview_payload_exposes_real_run_context_and_diagnostics():
    payload = d13_preview_payload(_decision())

    assert payload["status"] == "READY"
    assert payload["mode"] == "READ_ONLY_D13_PREVIEW"
    assert payload["gameplay_command_sent"] is False
    assert payload["phase"] == "BLIND_SELECT"
    assert payload["checkpoint_sequence"] == 17
    assert payload["deck"] == "RED"
    assert payload["stake"] == "WHITE"
    assert payload["ante"] == 3
    assert payload["money"] == 11
    assert payload["blind_type"] == "BIG"
    assert payload["tag_key"] == "tag_negative"
    assert payload["recommended_action"] == "SKIP_BLIND"
    assert payload["diagnostics"]["layer"] == "D13"


def test_d13_preview_blocks_non_blind_select_without_executing():
    payload = d13_preview_payload(_decision(phase="SHOP", source="shop policy"))

    assert payload["status"] == "BLOCKED_NOT_BLIND_SELECT"
    assert payload["gameplay_command_sent"] is False


def test_collect_d13_preview_calls_decide_only():
    runner = _Runner(_decision())

    payload = collect_d13_preview(
        observer_factory=_Observer,
        runner_factory=lambda observer: runner,
    )

    assert payload["status"] == "READY"
    assert runner.execute_called is False
