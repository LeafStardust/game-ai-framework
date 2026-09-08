import pytest

from games.balatro.env.strategic_evidence import buy_joker_with_public_evidence
from games.balatro.env.transition import HeadlessRunState
from games.balatro.live.parity_capture import (
    compare_run_rows_to_simulator_joker_purchase_evidence,
    successful_joker_purchase_evidence_from_run_rows,
)


def _shop_state(*, sequence, money, shop_cards, jokers=()):
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
            "shop_jokers": {"cards": list(shop_cards)},
        },
    }


def _joker(*, area_index, live_id="joker-1"):
    return {
        "ability_set": "JOKER",
        "area_index": area_index,
        "live_id": live_id,
        "center": "j_joker",
        "label": "Joker",
        "rarity": "COMMON",
        "cost": 2,
        "base_cost": 2,
    }


def _rows(*, action=None, success=True):
    target = _joker(area_index=1)
    action = action or {
        "name": "BUY_JOKER",
        "target": {"area_index": 1, "label": "Joker", "center": "j_joker", "cost": 2},
    }
    before_cards = [
        {"ability_set": "TAROT", "area_index": 0, "center": "c_strength", "cost": 3},
        target,
    ]
    return [
        {"event": "observation", "data": {"state": _shop_state(sequence=10, money=8, shop_cards=before_cards)}},
        {"event": "decision", "data": {"action": action}},
        {
            "event": "action_result",
            "data": {
                "action": action,
                "success": success,
                "state": _shop_state(sequence=11, money=6, shop_cards=before_cards[:1], jokers=[target]),
            },
        },
    ]


def test_env_r5_live_joker_purchase_maps_combined_area_index_to_filtered_joker_slot():
    evidence = successful_joker_purchase_evidence_from_run_rows(_rows())

    assert len(evidence) == 1
    transition = evidence[0]
    assert transition.action.alias == "BUY_JOKER"
    assert transition.action.payload() == {"slot": 0}
    assert transition.before.money == 8
    assert transition.after.money == 6
    assert len(transition.before.shop_jokers) == 1
    assert transition.after.shop_jokers == []
    assert len(transition.after.jokers) == 1


def test_env_r5_live_joker_purchase_fails_closed_on_unresolved_target():
    action = {"name": "BUY_JOKER", "target": {"area_index": 7}}
    with pytest.raises(ValueError, match="does not identify exactly one"):
        successful_joker_purchase_evidence_from_run_rows(_rows(action=action))


def test_env_r5_live_joker_purchase_rejects_failed_or_mismatched_result():
    with pytest.raises(ValueError, match="requires a successful action_result"):
        successful_joker_purchase_evidence_from_run_rows(_rows(success=False))

    rows = _rows()
    rows[2]["data"]["action"] = {"name": "BUY_JOKER", "target": {"area_index": 0}}
    with pytest.raises(ValueError, match="does not match captured decision"):
        successful_joker_purchase_evidence_from_run_rows(rows)


def test_env_r5_headless_joker_purchase_replays_translated_live_before_state():
    live_rows = _rows()
    live = successful_joker_purchase_evidence_from_run_rows(live_rows)
    before = live[0].before
    purchased = before.shop_jokers[0]
    run = HeadlessRunState(public=before, seed="r5-joker-purchase-parity")

    result, simulator = buy_joker_with_public_evidence(run, slot=0)

    assert run.public.money == 8
    assert run.public.shop_jokers == [purchased]
    assert result.public.money == 6
    assert result.public.shop_jokers == []
    assert len(result.public.jokers) == 1
    acquired = result.public.jokers[0]
    assert type(acquired) is type(purchased)
    assert (
        acquired.live_id,
        acquired.area_index,
        acquired.center,
        acquired.label,
        acquired.rarity,
        acquired.cost,
        acquired.base_cost,
    ) == (
        purchased.live_id,
        purchased.area_index,
        purchased.center,
        purchased.label,
        purchased.rarity,
        purchased.cost,
        purchased.base_cost,
    )
    comparison = compare_run_rows_to_simulator_joker_purchase_evidence(
        live_rows,
        (simulator,),
    )
    assert comparison.matches is True
    assert comparison.differences == ()
