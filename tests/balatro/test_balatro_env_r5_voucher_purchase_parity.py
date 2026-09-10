import json

import pytest

from games.balatro.env.strategic_evidence import buy_voucher_with_public_evidence
from games.balatro.env.transition import HeadlessRunState
from games.balatro.live.parity_capture import (
    compare_run_rows_to_simulator_voucher_purchase_evidence,
    successful_voucher_purchase_evidence_from_run_rows,
)
from games.balatro.live.voucher_purchase_fixture import (
    VoucherPurchaseFixtureError,
    preserve_successful_voucher_purchase_fixture,
)


_SCHEMA = "balatro-run-experience-v1"


def _voucher(*, center="v_wasteful", label="Wasteful", area_index=0):
    return {
        "ability_set": "Voucher",
        "area_index": area_index,
        "live_id": "voucher-1",
        "center": center,
        "label": label,
        "cost": 10,
        "sell_cost": 5,
    }


def _shop_state(
    *,
    sequence,
    money,
    shop_vouchers,
    vouchers=(),
    discards=4,
    shop_discount_percent=0,
    tarot_rate=4.0,
    planet_rate=4.0,
):
    return {
        "sequence": sequence,
        "phase": "SHOP",
        "state_complete": True,
        "payload": {
            "deck": "RED",
            "stake": "WHITE",
            "money": money,
            "round": {
                "hands_left": 4,
                "discards_left": discards,
                "discards_total": discards,
                "discards_used": 0,
                "chips": 0,
            },
            "round_reset_discards": discards,
            "round_reset_discards_observed": True,
            "hand": {"limit": 8, "cards": []},
            "cards": {"cards": []},
            "jokers": {"limit": 5, "cards": []},
            "shop_jokers": {"cards": []},
            "shop_vouchers": {"limit": 1, "cards": list(shop_vouchers)},
            "vouchers": list(vouchers),
            "vouchers_observed": True,
            "shop_discount_percent": shop_discount_percent,
            "shop_discount_percent_observed": True,
            "tarot_rate": tarot_rate,
            "planet_rate": planet_rate,
        },
    }


def _row(event, data, sequence):
    return {
        "schema": _SCHEMA,
        "run_id": "r5-voucher-purchase",
        "deck": "RED",
        "stake": "WHITE",
        "sequence": sequence,
        "event": event,
        "data": data,
    }


def _rows(*, voucher=None, action=None, result_action=None, success=True):
    voucher = voucher or _voucher()
    action = action or {
        "name": "BUY_VOUCHER",
        "target": {
            "area_index": voucher["area_index"],
            "center": voucher["center"],
            "label": voucher["label"],
            "price": voucher["cost"],
        },
    }
    result_action = action if result_action is None else result_action
    return [
        _row(
            "observation",
            {
                "state": _shop_state(
                    sequence=10,
                    money=25,
                    shop_vouchers=[voucher],
                    vouchers=[],
                    discards=4,
                )
            },
            100,
        ),
        _row("build_intent", {"transition": "BUILD_UPDATED"}, 101),
        _row("decision", {"action": action}, 102),
        _row(
            "action_result",
            {
                "action": result_action,
                "success": success,
                "state": _shop_state(
                    sequence=11,
                    money=15,
                    shop_vouchers=[],
                    vouchers=[voucher["center"]],
                    discards=5,
                ),
            },
            103,
        ),
    ]


def test_env_r5_live_voucher_purchase_maps_voucher_area_index_to_slot():
    evidence = successful_voucher_purchase_evidence_from_run_rows(_rows())

    assert len(evidence) == 1
    transition = evidence[0]
    assert transition.action.alias == "BUY_VOUCHER"
    assert transition.action.payload() == {"slot": 0}
    assert transition.before.money == 25
    assert transition.after.money == 15
    assert transition.before.round_reset_discards == 4
    assert transition.after.round_reset_discards == 5
    assert transition.before.discards_remaining == 4
    assert transition.after.discards_remaining == 5
    assert transition.before.vouchers == []
    assert transition.after.vouchers == ["v_wasteful"]
    assert len(transition.before.shop_vouchers) == 1
    assert transition.after.shop_vouchers == []


def test_env_r5_live_seed_money_purchase_preserves_money_and_interest_cap_order():
    rows = _rows(voucher=_voucher(center="v_seed_money", label="Seed Money"))
    rows[0]["data"]["state"]["payload"].update(
        interest_cap_observed=True,
        interest_cap=25,
    )
    rows[3]["data"]["state"]["payload"].update(
        interest_cap_observed=True,
        interest_cap=50,
    )

    evidence = successful_voucher_purchase_evidence_from_run_rows(rows)
    transition = evidence[0]

    assert transition.before.money == 25
    assert transition.after.money == 15
    assert transition.before.interest_cap_observed is True
    assert transition.before.interest_cap == 25
    assert transition.after.interest_cap_observed is True
    assert transition.after.interest_cap == 50


def test_env_r5_live_clearance_sale_purchase_preserves_money_and_discount_order():
    voucher = _voucher(center="v_clearance_sale", label="Clearance Sale")
    rows = _rows(voucher=voucher)
    rows[0]["data"]["state"]["payload"].update(shop_discount_percent=0)
    rows[3]["data"]["state"]["payload"].update(shop_discount_percent=25)

    evidence = successful_voucher_purchase_evidence_from_run_rows(rows)
    transition = evidence[0]

    assert transition.before.money == 25
    assert transition.after.money == 15
    assert transition.before.shop_discount_percent_observed is True
    assert transition.before.shop_discount_percent == 0
    assert transition.after.shop_discount_percent_observed is True
    assert transition.after.shop_discount_percent == 25
    assert transition.after.vouchers == ["v_clearance_sale"]


def test_env_r5_live_liquidation_purchase_preserves_upgrade_order():
    voucher = _voucher(center="v_liquidation", label="Liquidation")
    rows = _rows(voucher=voucher)
    rows[0]["data"]["state"]["payload"].update(
        vouchers=["v_clearance_sale"],
        shop_discount_percent=25,
    )
    rows[3]["data"]["state"]["payload"].update(
        vouchers=["v_clearance_sale", "v_liquidation"],
        shop_discount_percent=50,
    )

    evidence = successful_voucher_purchase_evidence_from_run_rows(rows)
    transition = evidence[0]

    assert transition.before.money == 25
    assert transition.after.money == 15
    assert transition.before.shop_discount_percent == 25
    assert transition.after.shop_discount_percent == 50
    assert transition.after.vouchers == ["v_clearance_sale", "v_liquidation"]


def test_env_r5_live_reroll_surplus_purchase_preserves_public_economy_order():
    voucher = _voucher(center="v_reroll_surplus", label="Reroll Surplus")
    rows = _rows(voucher=voucher)

    evidence = successful_voucher_purchase_evidence_from_run_rows(rows)
    transition = evidence[0]

    assert transition.before.money == 25
    assert transition.after.money == 15
    assert transition.before.vouchers == []
    assert transition.after.vouchers == ["v_reroll_surplus"]


def test_env_r5_live_planet_merchant_purchase_preserves_rate_order():
    voucher = _voucher(center="v_planet_merchant", label="Planet Merchant")
    rows = _rows(voucher=voucher)
    rows[0]["data"]["state"]["payload"].update(planet_rate=4.0)
    rows[3]["data"]["state"]["payload"].update(
        planet_rate=9.6,
        vouchers=["v_planet_merchant"],
    )

    evidence = successful_voucher_purchase_evidence_from_run_rows(rows)
    transition = evidence[0]

    assert transition.before.money == 25
    assert transition.after.money == 15
    assert transition.before.planet_rate == 4.0
    assert transition.after.planet_rate == 9.6
    assert transition.after.vouchers == ["v_planet_merchant"]


def test_env_r5_live_voucher_purchase_rejects_wrong_identity_and_unsupported_center():
    with pytest.raises(ValueError, match="target center does not match"):
        successful_voucher_purchase_evidence_from_run_rows(
            _rows(
                action={
                    "name": "BUY_VOUCHER",
                    "target": {"area_index": 0, "center": "v_grabber"},
                }
            )
        )

    telescope = _voucher(center="v_telescope", label="Telescope")
    with pytest.raises(ValueError, match="exact redeemable Voucher subset"):
        successful_voucher_purchase_evidence_from_run_rows(_rows(voucher=telescope))


def test_env_r5_live_voucher_purchase_rejects_failed_or_mismatched_result():
    with pytest.raises(ValueError, match="requires a successful action_result"):
        successful_voucher_purchase_evidence_from_run_rows(_rows(success=False))

    with pytest.raises(ValueError, match="does not match captured decision"):
        successful_voucher_purchase_evidence_from_run_rows(
            _rows(
                result_action={
                    "name": "BUY_VOUCHER",
                    "target": {
                        "area_index": 0,
                        "center": "v_grabber",
                        "label": "Grabber",
                        "price": 10,
                    },
                }
            )
        )


def test_env_r5_headless_wasteful_purchase_replays_translated_live_before_state():
    live_rows = _rows()
    live = successful_voucher_purchase_evidence_from_run_rows(live_rows)
    before = live[0].before
    purchased = before.shop_vouchers[0]
    run = HeadlessRunState(public=before, seed="r5-voucher-purchase-parity")

    result, simulator = buy_voucher_with_public_evidence(run, slot=0)

    assert run.public.money == 25
    assert run.public.vouchers == []
    assert run.public.round_reset_discards == 4
    assert result.public.money == 15
    assert result.public.shop_vouchers == []
    assert result.public.vouchers == ["v_wasteful"]
    assert result.public.round_reset_discards == 5
    assert result.public.discards_remaining == 5
    assert purchased.center == "v_wasteful"

    comparison = compare_run_rows_to_simulator_voucher_purchase_evidence(
        live_rows,
        (simulator,),
    )
    assert comparison.matches is True
    assert comparison.differences == ()


def test_env_r5_voucher_fixture_preserver_is_opt_in_and_keeps_boundary_rows_exact(
    tmp_path,
):
    rows = _rows()
    raw_lines = [json.dumps(row, separators=(",", ":")) + "\n" for row in rows]
    source = tmp_path / "run.jsonl"
    destination = tmp_path / "fixture.jsonl"
    source.write_text("".join(raw_lines), encoding="utf-8")

    assert destination.exists() is False
    selected = preserve_successful_voucher_purchase_fixture(source, destination)

    assert [row["event"] for row in selected] == [
        "observation",
        "decision",
        "action_result",
    ]
    assert destination.read_text(encoding="utf-8") == "".join(
        [raw_lines[0], raw_lines[2], raw_lines[3]]
    )


def test_env_r5_voucher_fixture_preserver_fails_closed_on_mismatch(tmp_path):
    rows = _rows(
        result_action={
            "name": "BUY_VOUCHER",
            "target": {
                "area_index": 0,
                "center": "v_grabber",
                "label": "Grabber",
                "price": 10,
            },
        }
    )
    source = tmp_path / "mismatched.jsonl"
    source.write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )

    with pytest.raises(VoucherPurchaseFixtureError, match="does not match captured decision"):
        preserve_successful_voucher_purchase_fixture(
            source,
            tmp_path / "fixture.jsonl",
        )
