from copy import deepcopy

import pytest

from games.balatro.env.strategic_evidence import use_planet_with_public_evidence
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.live.parity_capture import (
    compare_run_rows_to_simulator_held_planet_use_evidence,
    successful_held_planet_use_evidence_from_run_rows,
)


def _state(*, sequence: int, phase: str = "SHOP", planet=True, level=1):
    consumables = (
        [
            {
                "ability_name": "Pluto",
                "ability_set": "Planet",
                "area_index": 2,
                "cost": 3,
                "label": "Pluto",
                "live_id": 41,
            }
        ]
        if planet is True
        else planet if isinstance(planet, list) else []
    )
    return {
        "sequence": sequence,
        "phase": phase,
        "state_complete": True,
        "payload": {
            "deck": "RED",
            "stake": "WHITE",
            "money": 10,
            "round": {"hands_left": 4, "discards_left": 3, "chips": 0},
            "hand": {"limit": 8, "cards": []},
            "cards": {"cards": []},
            "jokers": {"limit": 5, "count": 0, "cards": []},
            "consumables": {
                "limit": 2,
                "count": len(consumables),
                "cards": consumables,
            },
            "hands": {"High Card": {"level": level}},
            "last_tarot_planet": "c_pluto" if level > 1 else None,
        },
    }


def _action(*, name="Pluto", area_index=2, indices=None):
    action = {
        "name": "USE_CONSUMABLE",
        "target": {"area_index": area_index, "name": name, "price": 3},
    }
    if indices is not None:
        action["indices"] = indices
    return action


def _rows(*, action=None, before=None, after=None, success=True):
    action = action or _action()
    before = before or _state(sequence=10)
    after = after or _state(sequence=11, planet=False, level=2)
    return [
        {"event": "observation", "data": {"state": before}},
        {"event": "decision", "data": {"action": deepcopy(action)}},
        {
            "event": "action_result",
            "data": {
                "action": deepcopy(action),
                "state": after,
                "success": success,
            },
        },
    ]


def _exact_run(before):
    return HeadlessRunState(
        public=before,
        seed="R5-HELD-PLANET",
        consumable_usage_observed=True,
        consumable_usage_counts={},
        consumable_usage_totals={"planet": 0, "tarot_planet": 0, "all": 0},
    )


def test_env_r5_held_planet_use_maps_visible_target_to_translated_index():
    evidence = successful_held_planet_use_evidence_from_run_rows(_rows())

    assert len(evidence) == 1
    assert evidence[0].action.alias == "USE_CONSUMABLE"
    assert evidence[0].action.payload() == {"consumable_index": 0}
    assert evidence[0].before.consumables[0].name == "Pluto"
    assert evidence[0].after.consumables == []
    assert evidence[0].before.hand_levels["HIGH_CARD"] == 1
    assert evidence[0].after.hand_levels["HIGH_CARD"] == 2


def test_env_r5_held_planet_use_replays_through_exact_owner_and_compares():
    rows = _rows()
    live = successful_held_planet_use_evidence_from_run_rows(rows)[0]

    result, simulator = use_planet_with_public_evidence(
        _exact_run(live.before),
        consumable_index=live.action.payload()["consumable_index"],
    )
    comparison = compare_run_rows_to_simulator_held_planet_use_evidence(
        rows,
        (simulator,),
    )

    assert result.public.consumables == []
    assert result.public.hand_levels["HIGH_CARD"] == 2
    assert result.public.last_tarot_planet == "c_pluto"
    assert result.consumable_usage_counts == {"c_pluto": 1}
    assert result.consumable_usage_totals == {
        "planet": 1,
        "tarot_planet": 1,
        "all": 1,
    }
    assert comparison.matches is True
    assert comparison.differences == ()


def test_env_r5_held_planet_public_evidence_admits_selecting_hand_boundary():
    rows = _rows(
        before=_state(sequence=10, phase="SELECTING_HAND"),
        after=_state(sequence=11, phase="SELECTING_HAND", planet=False, level=2),
    )

    evidence = successful_held_planet_use_evidence_from_run_rows(rows)

    assert len(evidence) == 1
    assert evidence[0].before.phase == "SELECTING_HAND"
    assert evidence[0].after.phase == "SELECTING_HAND"


def test_env_r5_held_planet_use_reports_public_post_state_difference():
    rows = _rows(after=_state(sequence=11, planet=False, level=3))
    live = successful_held_planet_use_evidence_from_run_rows(rows)[0]
    _, simulator = use_planet_with_public_evidence(
        _exact_run(live.before),
        consumable_index=0,
    )

    comparison = compare_run_rows_to_simulator_held_planet_use_evidence(
        rows,
        (simulator,),
    )

    assert comparison.matches is False
    assert comparison.differences == ("step[0].after",)


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        (_rows(action=_action(indices=[])), "must not target hand cards"),
        (_rows(action=_action(name="Mercury")), "name does not match"),
        (_rows(action=_action(area_index=True)), "nonnegative integer"),
        (
            _rows(
                before=_state(
                    sequence=10,
                    planet=[
                        {
                            "ability_name": "The Hermit",
                            "ability_set": "Tarot",
                            "area_index": 2,
                            "label": "The Hermit",
                            "live_id": 41,
                        }
                    ],
                )
            ),
            "not an exact held Planet",
        ),
        (
            _rows(before=_state(sequence=10, phase="SELECTING_HAND")),
            "same supported phase",
        ),
        (_rows(success=False), "requires a successful"),
    ],
)
def test_env_r5_held_planet_use_fails_closed_outside_exact_public_subset(
    rows,
    message,
):
    with pytest.raises(ValueError, match=message):
        successful_held_planet_use_evidence_from_run_rows(rows)


def test_env_r5_held_planet_evidence_wrapper_requires_private_usage_history():
    before = successful_held_planet_use_evidence_from_run_rows(_rows())[0].before
    run = HeadlessRunState(public=before, seed="R5-NO-USAGE-AUTHORITY")

    with pytest.raises(HeadlessTransitionError, match="usage history"):
        use_planet_with_public_evidence(run, consumable_index=0)
