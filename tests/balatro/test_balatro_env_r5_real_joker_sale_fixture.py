import hashlib
import json
from pathlib import Path

from games.balatro.env.strategic_evidence import sell_joker_with_public_evidence
from games.balatro.env.transition import HeadlessRunState
from games.balatro.live.parity_capture import (
    compare_run_rows_to_simulator_joker_sale_evidence,
    successful_joker_sale_evidence_from_run_rows,
)


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "r5"
    / "balatro-20260911T113953Z-d9e2aa91-attempt-004.sell-jolly-joker.jsonl"
)
_FIXTURE_SHA256 = "36a1ac8e5eb9f7ec6d6d485a14002810e0f78c4849f107674d4e869ba91401ec"


def _fixture_rows():
    return [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines()]


def test_env_r5_real_jolly_joker_sale_preserves_exact_live_boundary():
    raw = FIXTURE.read_bytes()
    rows = _fixture_rows()

    canonical_raw = raw.replace(b"\r\n", b"\n")
    assert hashlib.sha256(canonical_raw).hexdigest() == _FIXTURE_SHA256
    assert [row["sequence"] for row in rows] == [234, 235, 236]
    assert [row["event"] for row in rows] == [
        "observation",
        "decision",
        "action_result",
    ]
    assert rows[1]["data"]["action"] == {
        "name": "SELL_JOKER",
        "target": {"joker_index": 1},
    }
    assert rows[2]["data"]["success"] is True

    live = successful_joker_sale_evidence_from_run_rows(rows)
    assert len(live) == 1
    transition = live[0]

    assert transition.action.payload() == {"joker_index": 1}
    assert transition.before.money == 38
    assert transition.after.money == 39
    assert [joker.center for joker in transition.before.jokers] == [
        "j_wrathful_joker",
        "j_jolly",
        "j_sly",
        "j_stencil",
        "j_misprint",
    ]
    assert [joker.center for joker in transition.after.jokers] == [
        "j_wrathful_joker",
        "j_sly",
        "j_stencil",
        "j_misprint",
    ]
    assert "j_jolly" not in {
        record["key"]
        for record in transition.before.joker_generation_pools["1"]
    }
    assert "j_jolly" in {
        record["key"]
        for record in transition.after.joker_generation_pools["1"]
    }


def test_env_r5_real_jolly_joker_sale_replays_through_exact_owner():
    rows = _fixture_rows()
    live = successful_joker_sale_evidence_from_run_rows(rows)
    transition = live[0]
    run = HeadlessRunState(public=transition.before, seed="r5-real-jolly-joker-sale")

    result, simulator = sell_joker_with_public_evidence(run, joker_index=1)
    comparison = compare_run_rows_to_simulator_joker_sale_evidence(
        rows,
        (simulator,),
    )

    assert result.public.money == 39
    assert [joker.center for joker in result.public.jokers] == [
        "j_wrathful_joker",
        "j_sly",
        "j_stencil",
        "j_misprint",
    ]
    assert "j_jolly" not in {
        record["key"] for record in run.public.joker_generation_pools["1"]
    }
    assert "j_jolly" in {
        record["key"] for record in result.public.joker_generation_pools["1"]
    }
    assert comparison.matches is True
    assert comparison.differences == ()
