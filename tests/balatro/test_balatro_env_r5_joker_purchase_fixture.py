import gzip
import json
from pathlib import Path

import pytest

from games.balatro.env.strategic_evidence import buy_joker_with_public_evidence
from games.balatro.env.transition import HeadlessRunState
from games.balatro.live.joker_purchase_fixture import (
    JokerPurchaseFixtureError,
    preserve_successful_joker_purchase_fixture,
)
from games.balatro.live.parity_capture import (
    compare_run_rows_to_simulator_joker_purchase_evidence,
    successful_joker_purchase_evidence_from_run_rows,
)


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "r5"
    / "balatro-20260831T082151Z-78326f05-attempt-001.buy-juggler.jsonl.gz"
)


def _fixture_text():
    with gzip.open(FIXTURE, "rt", encoding="utf-8", newline="") as handle:
        return handle.read()


def _fixture_rows():
    return [json.loads(line) for line in _fixture_text().splitlines()]


def test_env_r5_real_juggler_purchase_fixture_preserves_public_boundary():
    rows = _fixture_rows()

    assert [row["sequence"] for row in rows] == [47, 48, 49]
    assert [row["event"] for row in rows] == ["observation", "decision", "action_result"]
    action = rows[1]["data"]["action"]
    assert action == {
        "name": "BUY_JOKER",
        "target": {
            "area_index": 1,
            "center": "j_juggler",
            "cost": 4.0,
            "label": "Juggler",
        },
    }

    live = successful_joker_purchase_evidence_from_run_rows(rows)
    assert len(live) == 1
    transition = live[0]
    assert transition.action.payload() == {"slot": 1}
    assert transition.before.money == 14
    assert transition.after.money == 10
    assert transition.before.hand_size == 8
    assert transition.after.hand_size == 9
    assert [type(joker).__name__ for joker in transition.before.shop_jokers] == [
        "CraftyJoker",
        "JugglerJoker",
    ]
    assert [type(joker).__name__ for joker in transition.after.shop_jokers] == [
        "CraftyJoker"
    ]
    assert [type(joker).__name__ for joker in transition.after.jokers] == ["JugglerJoker"]


def test_env_r5_real_juggler_purchase_fixture_replays_unchanged_through_headless_owner():
    rows = _fixture_rows()
    live = successful_joker_purchase_evidence_from_run_rows(rows)
    transition = live[0]
    slot = transition.action.payload()["slot"]
    run = HeadlessRunState(public=transition.before, seed="r5-real-juggler-purchase")

    _result, simulator = buy_joker_with_public_evidence(run, slot=slot)
    comparison = compare_run_rows_to_simulator_joker_purchase_evidence(rows, (simulator,))

    assert comparison.matches is True
    assert comparison.differences == ()


def test_env_r5_purchase_fixture_preserver_is_opt_in_and_keeps_selected_rows_exact(tmp_path):
    source = tmp_path / "run.jsonl"
    destination = tmp_path / "fixture.jsonl"
    fixture_text = _fixture_text()
    source.write_text(fixture_text, encoding="utf-8")

    assert destination.exists() is False
    selected = preserve_successful_joker_purchase_fixture(source, destination)

    assert destination.read_text(encoding="utf-8") == fixture_text
    assert [row["event"] for row in selected] == ["observation", "decision", "action_result"]


def test_env_r5_purchase_fixture_preserver_fails_closed_on_mismatched_result(tmp_path):
    rows = _fixture_rows()
    rows[2]["data"]["action"] = {
        "name": "BUY_JOKER",
        "target": {
            "area_index": 0,
            "center": "j_crafty",
            "cost": 4.0,
            "label": "Crafty Joker",
        },
    }
    source = tmp_path / "mismatched.jsonl"
    source.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(JokerPurchaseFixtureError, match="does not match captured decision"):
        preserve_successful_joker_purchase_fixture(source, tmp_path / "fixture.jsonl")
