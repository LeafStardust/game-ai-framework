from copy import deepcopy

import pytest

from games.balatro.env.strategic_evidence import (
    choose_pack_option_with_public_evidence,
    skip_pack_with_public_evidence,
)
from games.balatro.env.transition import HeadlessRunState
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.red_card import RedCardJoker
from games.balatro.live.parity_capture import (
    compare_run_rows_to_simulator_buffoon_pack_evidence,
    successful_buffoon_pack_evidence_from_run_rows,
)
from games.balatro.state import BalatroState


def _log_state(*, sequence: int, phase: str, jokers=()):
    return {
        "sequence": sequence,
        "phase": phase,
        "state_complete": True,
        "payload": {
            "deck": "RED",
            "stake": "WHITE",
            "money": 12,
            "round": {"hands_left": 4, "discards_left": 3, "chips": 0},
            "hand": {"limit": 8, "cards": []},
            "cards": {"cards": []},
            "jokers": {"limit": 5, "cards": list(jokers)},
        },
    }


def _rows(action, *, after_jokers=(), success=True):
    return [
        {
            "event": "observation",
            "data": {"state": _log_state(sequence=1, phase="BUFFOON_PACK")},
        },
        {"event": "decision", "data": {"action": deepcopy(action)}},
        {
            "event": "action_result",
            "data": {
                "action": deepcopy(action),
                "success": success,
                "state": _log_state(
                    sequence=2,
                    phase="SHOP",
                    jokers=after_jokers,
                ),
            },
        },
    ]


def _pack_run(*, with_red_card=False):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BUFFOON_PACK"
    state.shop_active = False
    if with_red_card:
        red_card = RedCardJoker()
        red_card.live_id = 10
        red_card.mult = 6
        state.jokers = [red_card]
    choice = FlatMultJoker()
    choice.live_id = 20
    return HeadlessRunState(
        public=state,
        seed="R5-BUFFOON",
        pack_choices=[choice],
        pack_return_phase="SHOP",
        pack_choices_remaining=1,
    )


def test_env_r5_buffoon_rows_use_frozen_choice_and_skip_actions():
    choice = {"name": "SELECT_PACK_CARD", "target": {"area_index": 0, "label": "Joker"}}
    joker = {
        "ability_name": "Joker",
        "ability_set": "Joker",
        "center": "j_joker",
        "label": "Joker",
        "live_id": 20,
        "rarity": "COMMON",
    }
    selected = successful_buffoon_pack_evidence_from_run_rows(
        _rows(choice, after_jokers=(joker,))
    )
    skipped = successful_buffoon_pack_evidence_from_run_rows(
        _rows({"name": "SKIP_BOOSTER"})
    )

    assert selected[0].action.alias == "CHOOSE_PACK_OPTION"
    assert selected[0].action.action_id == "SELECT_PACK_CARD"
    assert selected[0].action.payload() == {"option_index": 0}
    assert skipped[0].action.alias == "SKIP_PACK"
    assert skipped[0].action.action_id == "SKIP_BOOSTER"
    assert skipped[0].action.params == ()


@pytest.mark.parametrize(
    ("action", "message"),
    [
        ({"name": "SELECT_PACK_CARD", "target": {"area_index": 0}}, "visible identity"),
        ({"name": "SELECT_PACK_CARD", "target": {"area_index": True, "label": "Joker"}}, "area_index"),
        ({"name": "SKIP_BOOSTER", "target": {"area_index": 0}}, "must not contain parameters"),
    ],
)
def test_env_r5_buffoon_rows_fail_closed_on_inexact_actions(action, message):
    with pytest.raises(ValueError, match=message):
        successful_buffoon_pack_evidence_from_run_rows(_rows(action))


def test_env_r5_buffoon_rows_reject_failed_or_nonfinal_boundaries():
    action = {"name": "SELECT_PACK_CARD", "target": {"area_index": 0, "label": "Joker"}}
    with pytest.raises(ValueError, match="successful action_result"):
        successful_buffoon_pack_evidence_from_run_rows(_rows(action, success=False))

    rows = _rows(action)
    rows[-1]["data"]["state"]["phase"] = "BUFFOON_PACK"
    with pytest.raises(ValueError, match="requires SHOP or BLIND_SELECT after"):
        successful_buffoon_pack_evidence_from_run_rows(rows)


def test_env_r5_buffoon_evidence_wraps_canonical_pack_owners():
    choice_result, choice_evidence = choose_pack_option_with_public_evidence(
        _pack_run(),
        option_index=0,
    )
    skip_result, skip_evidence = skip_pack_with_public_evidence(
        _pack_run(with_red_card=True)
    )

    assert choice_evidence.action.alias == "CHOOSE_PACK_OPTION"
    assert [type(joker) for joker in choice_evidence.after.jokers] == [
        type(joker) for joker in choice_result.public.jokers
    ]
    assert choice_evidence.after.jokers[0].live_id == 20
    assert choice_result.public.phase == "SHOP"
    assert skip_evidence.action.alias == "SKIP_PACK"
    assert skip_evidence.after.jokers[0].mult == skip_result.public.jokers[0].mult == 9
    assert skip_result.public.phase == "SHOP"


def test_env_r5_buffoon_entry_point_compares_ordered_public_evidence():
    rows = _rows({"name": "SKIP_BOOSTER"})
    simulator = successful_buffoon_pack_evidence_from_run_rows(rows)

    comparison = compare_run_rows_to_simulator_buffoon_pack_evidence(rows, simulator)

    assert comparison.matches is True
    assert comparison.differences == ()
    assert comparison.live_length == comparison.simulator_length == 1
