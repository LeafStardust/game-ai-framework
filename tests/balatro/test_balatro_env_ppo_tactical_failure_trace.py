import json

import pytest

from games.balatro.env.ppo_tactical_failure_trace import (
    PPOTacticalFailureTraceError,
    build_tactical_failure_trace,
    write_tactical_failure_trace,
)


SOURCE = "docs/balatro/BALATRO_PPO_PROMOTION_FAILURE_TRACE.json"


@pytest.fixture(scope="module")
def report():
    return build_tactical_failure_trace(SOURCE)


def test_tactical_failure_trace_reproduces_losses_and_exact_clears(report):
    assert [item["game_seed"] for item in report["episodes"]] == [
        "5C7469F4",
        "FE32359A",
    ]
    assert [item["production"]["terminal"]["score"] for item in report["episodes"]] == [204, 212]
    assert [
        item["exact_clearing_counterfactual"]["terminal"]["score"]
        for item in report["episodes"]
    ] == [396, 348]
    assert [item["first_divergence_index"] for item in report["episodes"]] == [0, 1]


def test_tactical_failure_trace_pins_first_corrected_actions(report):
    first, second = report["episodes"]
    assert first["production"]["steps"][0]["decision"]["action"] == {
        "name": "DISCARD_CARDS",
        "indices": [0, 2, 3, 4, 5],
    }
    assert first["exact_clearing_counterfactual"]["steps"][0]["action"] == {
        "name": "PLAY_CARDS",
        "indices": [2, 4, 5, 6, 7],
    }
    assert second["production"]["steps"][1]["decision"]["action"] == {
        "name": "PLAY_CARDS",
        "indices": [1, 2, 5, 6],
    }
    assert second["exact_clearing_counterfactual"]["steps"][1]["action"] == {
        "name": "DISCARD_CARDS",
        "indices": [0, 3, 4, 5, 6],
    }


def test_tactical_failure_trace_writes_canonical_digest(report, tmp_path):
    path = tmp_path / "trace.json"
    digest = write_tactical_failure_trace(report, path)
    content = path.read_bytes()
    assert len(digest) == 64
    assert content == json.dumps(
        json.loads(content), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def test_tactical_failure_trace_rejects_source_tampering(tmp_path):
    payload = json.loads(open(SOURCE, encoding="utf-8").read())
    payload["episodes"][0]["expected_action_count"] = 2
    path = tmp_path / "tampered.json"
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8"
    )
    with pytest.raises(PPOTacticalFailureTraceError, match="source drifted"):
        build_tactical_failure_trace(path)
