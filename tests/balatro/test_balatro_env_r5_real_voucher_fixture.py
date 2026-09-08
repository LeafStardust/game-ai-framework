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
