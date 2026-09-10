import hashlib
import json
import lzma
from pathlib import Path

from games.balatro.env.strategic_evidence import buy_voucher_with_public_evidence
from games.balatro.env.transition import HeadlessRunState
from games.balatro.live.parity_capture import (
    compare_run_rows_to_simulator_voucher_purchase_evidence,
    successful_voucher_purchase_evidence_from_run_rows,
)


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "r5"
    / "balatro-20260908T135908Z-3f93a77a-attempt-001.buy-paint-brush.jsonl.xz"
)
_FIXTURE_SHA256 = "36d25e575079e279c33d42e9df6cbd00467209fdc146ce0bd67395f2b3f0b7d3"
SEED_MONEY_FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "r5"
    / "balatro-r5-current-head-seed-money.buy-seed-money.jsonl"
)
_SEED_MONEY_FIXTURE_SHA256 = (
    "3fb42028b705699953bb30d636a3777b3732982d234db2cc4327b03b8ca83f10"
)


def _fixture_bytes() -> bytes:
    with lzma.open(FIXTURE, "rb") as handle:
        return handle.read()


def _fixture_rows():
    return [json.loads(line) for line in _fixture_bytes().decode("utf-8").splitlines()]


def test_env_r5_real_paint_brush_voucher_fixture_preserves_exact_live_boundary():
    raw = _fixture_bytes()
    rows = _fixture_rows()

    assert hashlib.sha256(raw).hexdigest() == _FIXTURE_SHA256
    assert [row["sequence"] for row in rows] == [59, 60, 61]
    assert [row["event"] for row in rows] == ["observation", "decision", "action_result"]
    assert rows[1]["data"]["action"] == {
        "name": "BUY_VOUCHER",
        "target": {
            "area_index": 0,
            "center": "v_paint_brush",
            "label": "Paint Brush",
            "price": 10,
        },
    }
    assert rows[2]["data"]["success"] is True

    live = successful_voucher_purchase_evidence_from_run_rows(rows)
    assert len(live) == 1
    transition = live[0]
    assert transition.action.payload() == {"slot": 0}
    assert transition.before.money == 18
    assert transition.after.money == 8
    assert transition.before.hand_size == 8
    assert transition.after.hand_size == 9
    assert transition.before.vouchers == []
    assert transition.after.vouchers == ["v_paint_brush"]
    assert len(transition.before.shop_vouchers) == 1
    assert transition.before.shop_vouchers[0].center == "v_paint_brush"
    assert transition.after.shop_vouchers == []


def test_env_r5_real_paint_brush_voucher_fixture_replays_unchanged_through_headless_owner():
    rows = _fixture_rows()
    live = successful_voucher_purchase_evidence_from_run_rows(rows)
    transition = live[0]
    slot = transition.action.payload()["slot"]
    run = HeadlessRunState(public=transition.before, seed="r5-real-paint-brush-voucher")

    result, simulator = buy_voucher_with_public_evidence(run, slot=slot)
    comparison = compare_run_rows_to_simulator_voucher_purchase_evidence(rows, (simulator,))

    assert result.public.money == 8
    assert result.public.hand_size == 9
    assert result.public.vouchers == ["v_paint_brush"]
    assert result.public.shop_vouchers == []
    assert comparison.matches is True
    assert comparison.differences == ()


def test_env_r5_real_seed_money_fixture_preserves_live_cap_transition():
    raw = SEED_MONEY_FIXTURE.read_bytes()
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines()]

    assert hashlib.sha256(raw).hexdigest() == _SEED_MONEY_FIXTURE_SHA256
    assert [row["event"] for row in rows] == [
        "observation",
        "decision",
        "action_result",
    ]
    assert rows[1]["data"]["action"]["target"]["center"] == "v_seed_money"
    assert rows[2]["data"]["success"] is True

    live = successful_voucher_purchase_evidence_from_run_rows(rows)
    transition = live[0]

    assert transition.before.money == 27
    assert transition.after.money == 17
    assert transition.before.interest_cap_observed is True
    assert transition.before.interest_cap == 25
    assert transition.after.interest_cap_observed is True
    assert transition.after.interest_cap == 50
    assert transition.after.vouchers == ["v_seed_money"]


def test_env_r5_real_seed_money_fixture_replays_unchanged_through_headless_owner():
    rows = [
        json.loads(line)
        for line in SEED_MONEY_FIXTURE.read_text(encoding="utf-8").splitlines()
    ]
    live = successful_voucher_purchase_evidence_from_run_rows(rows)
    transition = live[0]
    run = HeadlessRunState(public=transition.before, seed="r5-real-seed-money")

    result, simulator = buy_voucher_with_public_evidence(run, slot=0)
    comparison = compare_run_rows_to_simulator_voucher_purchase_evidence(
        rows,
        (simulator,),
    )

    assert result.public.money == 17
    assert result.public.interest_cap_observed is True
    assert result.public.interest_cap == 50
    assert result.public.vouchers == ["v_seed_money"]
    assert comparison.matches is True
    assert comparison.differences == ()
