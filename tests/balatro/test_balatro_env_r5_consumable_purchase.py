import pytest

from games.balatro.consumable import PlanetCard
from games.balatro.env.strategic_evidence import (
    buy_consumable_with_public_evidence,
)
from games.balatro.env.transition import HeadlessRunState
from games.balatro.live.consumable_purchase_parity import (
    successful_consumable_purchase_evidence_from_run_rows,
)
from games.balatro.state import BalatroState


def _shop_state(*, sequence, money, shop_cards, consumables=()):
    return {
        "sequence": sequence,
        "phase": "SHOP",
        "state_complete": True,
        "payload": {
            "deck": "RED",
            "stake": "WHITE",
            "money": money,
            "round": {"hands_left": 4, "discards_left": 3, "chips": 0},
            "hand": {"limit": 8, "cards": []},
            "cards": {"cards": []},
            "jokers": {"limit": 5, "cards": []},
            "consumables": {"limit": 2, "cards": list(consumables)},
            "shop_jokers": {"cards": list(shop_cards)},
        },
    }


def _planet(*, area_index, live_id="planet-1", label="Jupiter", cost=3):
    return {
        "ability_set": "PLANET",
        "area_index": area_index,
        "live_id": live_id,
        "label": label,
        "cost": cost,
    }


def _rows(*, action=None, success=True, target=None):
    target_item = _planet(area_index=1)
    joker = {
        "ability_set": "JOKER",
        "area_index": 0,
        "live_id": "joker-1",
        "center": "j_joker",
        "label": "Joker",
        "cost": 2,
    }
    action = action or {
        "name": "BUY_CONSUMABLE",
        "target": target
        or {"area_index": 1, "label": "Jupiter", "cost": 3},
    }
    before_cards = [joker, target_item]
    return [
        {
            "event": "observation",
            "data": {
                "state": _shop_state(
                    sequence=10,
                    money=10,
                    shop_cards=before_cards,
                )
            },
        },
        {"event": "decision", "data": {"action": action}},
        {
            "event": "action_result",
            "data": {
                "action": action,
                "success": success,
                "state": _shop_state(
                    sequence=11,
                    money=7,
                    shop_cards=[joker],
                    consumables=[target_item],
                ),
            },
        },
    ]


def test_env_r5_live_consumable_purchase_maps_combined_area_index_to_filtered_slot():
    evidence = successful_consumable_purchase_evidence_from_run_rows(_rows())

    assert len(evidence) == 1
    transition = evidence[0]
    assert transition.action.alias == "BUY_CONSUMABLE"
    assert transition.action.payload() == {"slot": 0}
    assert transition.before.money == 10
    assert transition.after.money == 7
    assert len(transition.before.shop_consumables) == 1
    assert transition.after.shop_consumables == []
    assert len(transition.after.consumables) == 1


def test_env_r5_live_consumable_purchase_fails_closed_on_unresolved_area_index():
    with pytest.raises(ValueError, match="does not identify exactly one"):
        successful_consumable_purchase_evidence_from_run_rows(
            _rows(target={"area_index": 7, "label": "Jupiter", "cost": 3})
        )


def test_env_r5_live_consumable_purchase_fails_closed_on_identity_or_cost_drift():
    with pytest.raises(ValueError, match="label"):
        successful_consumable_purchase_evidence_from_run_rows(
            _rows(target={"area_index": 1, "label": "Mars", "cost": 3})
        )

    with pytest.raises(ValueError, match="cost"):
        successful_consumable_purchase_evidence_from_run_rows(
            _rows(target={"area_index": 1, "label": "Jupiter", "cost": 4})
        )


def test_env_r5_live_consumable_purchase_rejects_failed_result():
    with pytest.raises(ValueError, match="successful action_result"):
        successful_consumable_purchase_evidence_from_run_rows(_rows(success=False))


def test_env_r5_headless_consumable_purchase_wraps_canonical_owner():
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = 10
    planet = PlanetCard("Jupiter", "PAIR", 10, 1)
    planet.price = 3
    planet.area_index = 0
    state.shop_consumables = [planet]
    state.consumable_slots = 2

    run = HeadlessRunState(public=state, seed="r5-consumable-purchase")
    result, evidence = buy_consumable_with_public_evidence(run, slot=0)

    assert run.public.money == 10
    assert result.public.money == 7
    assert result.public.shop_consumables == []
    assert len(result.public.consumables) == 1
    bought = result.public.consumables[0]
    assert bought.name == planet.name
    assert bought.category == planet.category
    assert bought.hand_type == planet.hand_type
    assert bought.chips == planet.chips
    assert bought.mult == planet.mult
    assert bought.price == planet.price
    assert bought.area_index == planet.area_index
    assert evidence.action.alias == "BUY_CONSUMABLE"
    assert evidence.action.payload() == {"slot": 0}
