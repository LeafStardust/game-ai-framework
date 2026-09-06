from copy import deepcopy

import pytest

from games.balatro.env.actions import EnvAction
from games.balatro.env.parity import compare_public_strategic_trajectory
from games.balatro.env.shop_main_generation import generate_base_main_shop
from games.balatro.env.strategic_evidence import (
    PublicStrategicTransitionEvidence,
    build_public_strategic_transition_evidence,
    reroll_shop_with_public_evidence,
)
from games.balatro.env.transition import HeadlessRunState
from games.balatro.live.parity_capture import (
    compare_run_rows_to_simulator_reroll_shop_evidence,
    successful_reroll_shop_evidence_from_run_rows,
)
from games.balatro.state import BalatroState


def _log_state(*, sequence, money):
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
        },
    }


def _reroll_rows(*, before_money=20, after_money=15, action=None, success=True):
    action = {"name": "REFRESH_SHOP"} if action is None else action
    return [
        {"event": "observation", "data": {"state": _log_state(sequence=1, money=before_money)}},
        {"event": "decision", "data": {"action": action}},
        {
            "event": "action_result",
            "data": {
                "action": action,
                "success": success,
                "state": _log_state(sequence=2, money=after_money),
            },
        },
    ]


def _joker_record(rarity, key, cost):
    return {"rarity": rarity, "key": key, "cost": cost, "unlocked": True, "no_pool_flag": None, "yes_pool_flag": None}


def _consumable_record(card_type, key, cost=3):
    return {"type": card_type, "key": key, "cost": cost, "unlocked": True, "no_pool_flag": None, "yes_pool_flag": None, "softlock": False, "hand_type": None}


def _generated_run(seed="R5-REROLL"):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.ante = 1
    state.money = 20
    state.shop_inflation_observed = True
    state.shop_inflation = 0
    state.shop_discount_percent_observed = True
    state.shop_discount_percent = 0
    state.joker_generation_pool_observed = True
    state.joker_generation_pools = {
        "1": [_joker_record(1, "j_joker", 2)],
        "2": [_joker_record(2, "j_stencil", 8)],
        "3": [_joker_record(3, "j_dna", 8)],
        "4": [_joker_record(4, "j_caino", 20)],
    }
    state.consumable_generation_pool_observed = True
    state.consumable_generation_pools = {
        "Tarot": [_consumable_record("Tarot", "c_strength")],
        "Planet": [_consumable_record("Planet", "c_pluto")],
    }
    return generate_base_main_shop(HeadlessRunState(public=state, seed=seed)).run


def test_env_r5_live_reroll_uses_frozen_r3_alias_and_production_action_id():
    evidence = successful_reroll_shop_evidence_from_run_rows(_reroll_rows())

    assert len(evidence) == 1
    assert evidence[0].action.alias == "REROLL_SHOP"
    assert evidence[0].action.action_id == "REFRESH_SHOP"
    assert evidence[0].action.params == ()
    assert evidence[0].before.money == 20
    assert evidence[0].after.money == 15


def test_env_r5_live_reroll_rejects_unexpected_action_parameters():
    rows = _reroll_rows(action={"name": "REFRESH_SHOP", "target": {"area_index": 0}})

    with pytest.raises(ValueError, match="must not contain parameters"):
        successful_reroll_shop_evidence_from_run_rows(rows)


def test_env_r5_live_reroll_rejects_failed_result():
    with pytest.raises(ValueError, match="requires a successful action_result"):
        successful_reroll_shop_evidence_from_run_rows(_reroll_rows(success=False))


def test_env_r5_live_reroll_rejects_action_result_without_matching_decision():
    rows = _reroll_rows()
    rows[1]["data"]["action"] = {"name": "END_SHOP"}

    with pytest.raises(ValueError, match="no captured decision boundary"):
        successful_reroll_shop_evidence_from_run_rows(rows)


def test_env_r5_strategic_trajectory_reports_action_param_state_and_length_differences():
    base_before = BalatroState()
    base_before.phase = "SHOP"
    base_before.money = 20
    base_after = deepcopy(base_before)
    base_after.money = 15
    live = build_public_strategic_transition_evidence(base_before, EnvAction.from_alias("REROLL_SHOP"), base_after)

    changed_after = deepcopy(base_after)
    changed_after.money = 14
    simulator = PublicStrategicTransitionEvidence(
        before=deepcopy(live.before),
        action=EnvAction.from_alias("REROLL_SHOP", {"unexpected": 1}),
        after=changed_after,
    )

    comparison = compare_public_strategic_trajectory((live, live), (simulator,))

    assert comparison.matches is False
    assert comparison.differences == ("length", "step[0].action.params", "step[0].after")
    assert comparison.live_length == 2
    assert comparison.simulator_length == 1


def test_env_r5_headless_reroll_evidence_wraps_canonical_owner_without_mutating_input():
    run = _generated_run()
    before_money = run.public.money
    before_rng = run.rng_snapshot()

    result, evidence = reroll_shop_with_public_evidence(run)

    assert evidence.action.alias == "REROLL_SHOP"
    assert evidence.action.action_id == "REFRESH_SHOP"
    assert evidence.before.money == before_money == 20
    assert evidence.after.money == result.run.public.money == 15
    assert run.public.money == 20
    assert run.rng_snapshot() == before_rng
    assert result.run.rng_snapshot() != before_rng


def test_env_r5_live_reroll_entry_point_compares_ordered_public_evidence():
    rows = _reroll_rows()
    simulator = successful_reroll_shop_evidence_from_run_rows(rows)

    comparison = compare_run_rows_to_simulator_reroll_shop_evidence(rows, simulator)

    assert comparison.matches is True
    assert comparison.differences == ()
    assert comparison.live_length == comparison.simulator_length == 1
