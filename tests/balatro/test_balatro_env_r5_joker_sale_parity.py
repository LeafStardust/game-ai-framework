import pytest

from games.balatro.env.strategic_evidence import sell_joker_with_public_evidence
from games.balatro.env.transition import HeadlessRunState
from games.balatro.live.parity_capture import (
    compare_run_rows_to_simulator_joker_sale_evidence,
    successful_joker_sale_evidence_from_run_rows,
)


def _joker(*, center="j_joker", live_id="joker-1", eternal=False, edition=None):
    value = {
        "ability_set": "JOKER",
        "area_index": 0,
        "live_id": live_id,
        "center": center,
        "label": "Joker",
        "rarity": "COMMON",
        "cost": 2,
        "base_cost": 2,
        "sell_cost": 1,
        "eternal": eternal,
    }
    if edition is not None:
        value["edition"] = edition
    return value


def _shop_state(*, sequence, money, jokers):
    return {
        "sequence": sequence,
        "phase": "SHOP",
        "state_complete": True,
        "payload": {
            "deck": "RED",
            "stake": "WHITE",
            "money": money,
            "round": {"hands_left": 4, "discards_left": 3, "chips": 300},
            "hand": {"limit": 8, "cards": []},
            "cards": {"cards": []},
            "jokers": {"limit": 5, "cards": list(jokers)},
            "shop_jokers": {"cards": []},
        },
    }


def _rows(*, joker=None, action=None, result_action=None, success=True):
    joker = joker or _joker()
    action = action or {"name": "SELL_JOKER", "target": {"joker_index": 0}}
    result_action = action if result_action is None else result_action
    return [
        {
            "event": "observation",
            "data": {"state": _shop_state(sequence=10, money=7, jokers=[joker])},
        },
        {"event": "decision", "data": {"action": action}},
        {
            "event": "action_result",
            "data": {
                "action": result_action,
                "success": success,
                "state": _shop_state(sequence=11, money=8, jokers=[]),
            },
        },
    ]


def test_env_r5_live_joker_sale_maps_exact_owned_index():
    evidence = successful_joker_sale_evidence_from_run_rows(_rows())

    assert len(evidence) == 1
    transition = evidence[0]
    assert transition.action.alias == "SELL_JOKER"
    assert transition.action.payload() == {"joker_index": 0}
    assert transition.before.money == 7
    assert transition.after.money == 8
    assert len(transition.before.jokers) == 1
    assert transition.after.jokers == []


@pytest.mark.parametrize(
    ("action", "message"),
    [
        ({"name": "SELL_JOKER"}, "exactly one target joker_index"),
        (
            {"name": "SELL_JOKER", "target": {"joker_index": True}},
            "integer joker_index",
        ),
        (
            {"name": "SELL_JOKER", "target": {"joker_index": 1}},
            "outside the translated owned Jokers",
        ),
        (
            {
                "name": "SELL_JOKER",
                "target": {"joker_index": 0, "center": "j_joker"},
            },
            "exactly one target joker_index",
        ),
    ],
)
def test_env_r5_live_joker_sale_rejects_malformed_or_ambiguous_target(action, message):
    with pytest.raises(ValueError, match=message):
        successful_joker_sale_evidence_from_run_rows(_rows(action=action))


@pytest.mark.parametrize(
    "joker",
    [
        _joker(center="j_juggler"),
        _joker(eternal=True),
        _joker(edition="FOIL"),
    ],
)
def test_env_r5_live_joker_sale_rejects_unsupported_inverse_or_metadata(joker):
    with pytest.raises(ValueError, match="exact inventory-only sale subset"):
        successful_joker_sale_evidence_from_run_rows(_rows(joker=joker))


def test_env_r5_live_joker_sale_rejects_failed_mismatched_or_non_shop_result():
    with pytest.raises(ValueError, match="requires a successful action_result"):
        successful_joker_sale_evidence_from_run_rows(_rows(success=False))

    with pytest.raises(ValueError, match="does not match captured decision"):
        successful_joker_sale_evidence_from_run_rows(
            _rows(
                result_action={
                    "name": "SELL_JOKER",
                    "target": {"joker_index": 1},
                }
            )
        )

    rows = _rows()
    rows[2]["data"]["state"]["phase"] = "BLIND_SELECT"
    with pytest.raises(ValueError, match="requires SHOP before and after"):
        successful_joker_sale_evidence_from_run_rows(rows)


def test_env_r5_headless_joker_sale_replays_translated_live_before_state():
    live_rows = _rows()
    live = successful_joker_sale_evidence_from_run_rows(live_rows)
    before = live[0].before
    sold = before.jokers[0]
    run = HeadlessRunState(public=before, seed="r5-joker-sale-parity")

    result, simulator = sell_joker_with_public_evidence(run, joker_index=0)

    assert run.public.money == 7
    assert run.public.jokers == [sold]
    assert result.public.money == 8
    assert result.public.jokers == []
    comparison = compare_run_rows_to_simulator_joker_sale_evidence(
        live_rows,
        (simulator,),
    )
    assert comparison.matches is True
    assert comparison.differences == ()
