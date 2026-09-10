from copy import deepcopy

from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS, BalatroAction
from games.balatro.card import BalatroCard
from games.balatro.env.parity import compare_public_tactical_trajectory
from games.balatro.env.tactical_evidence import PublicTacticalTransitionEvidence
from games.balatro.live.parity_capture import (
    compare_run_rows_to_simulator_tactical_evidence,
    successful_tactical_evidence_from_run_rows,
)
from games.balatro.state import BalatroState


def _state(*, score=0, rank="A", live_id="card"):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.deck = []
    state.hand = [BalatroCard(rank, "Spades", live_id=live_id)]
    state.score = score
    state.hands_remaining = 3
    return state


def _evidence(*, action_name=PLAY_CARDS, before_score=0, after_score=11, live_id="card"):
    before = _state(score=before_score, live_id=f"{live_id}-before")
    after = _state(score=after_score, live_id=f"{live_id}-after")
    return PublicTacticalTransitionEvidence(
        before=before,
        action=BalatroAction(action_name, cards=[before.hand[0]]),
        selected_hand_indices=(0,),
        after=after,
    )


def _log_state(*, sequence, score):
    return {
        "sequence": sequence,
        "phase": "SELECTING_HAND",
        "state_complete": True,
        "payload": {
            "score": score,
            "round": {"hands_left": 3, "discards_left": 3, "chips": 300},
            "hand": {
                "limit": 1,
                "cards": [
                    {"id": f"live-{sequence}", "value": {"rank": "A", "suit": "S"}}
                ],
            },
            "cards": {"cards": []},
        },
    }


def _rows(*, action_name=PLAY_CARDS, before_score=0, after_score=11):
    action = {"name": action_name, "indices": [0]}
    return [
        {
            "event": "observation",
            "data": {"state": _log_state(sequence=1, score=before_score)},
        },
        {"event": "decision", "data": {"action": action}},
        {
            "event": "action_result",
            "data": {
                "action": action,
                "success": True,
                "state": _log_state(sequence=2, score=after_score),
            },
        },
    ]


def test_env_r5_tactical_trajectory_matches_equivalent_ordered_steps():
    live = (
        _evidence(action_name=PLAY_CARDS, before_score=0, after_score=11, live_id="live-a"),
        _evidence(action_name=DISCARD_CARDS, before_score=11, after_score=11, live_id="live-b"),
    )
    simulator = (
        _evidence(action_name=PLAY_CARDS, before_score=0, after_score=11, live_id="sim-a"),
        _evidence(action_name=DISCARD_CARDS, before_score=11, after_score=11, live_id="sim-b"),
    )

    comparison = compare_public_tactical_trajectory(live, simulator)

    assert comparison.matches is True
    assert comparison.differences == ()
    assert comparison.live_length == 2
    assert comparison.simulator_length == 2
    assert len(comparison.steps) == 2


def test_env_r5_tactical_trajectory_reports_step_and_length_mismatches():
    live = (
        _evidence(action_name=PLAY_CARDS, before_score=0, after_score=11),
        _evidence(action_name=DISCARD_CARDS, before_score=11, after_score=11),
    )
    simulator_first = deepcopy(live[0])
    simulator_first.after.score = 12

    comparison = compare_public_tactical_trajectory(live, (simulator_first,))

    assert comparison.matches is False
    assert comparison.differences == ("length", "step[0].after")
    assert comparison.live_length == 2
    assert comparison.simulator_length == 1
    assert len(comparison.steps) == 1


def test_env_r5_run_log_entry_point_compares_against_simulator_evidence():
    rows = _rows()
    simulator = successful_tactical_evidence_from_run_rows(rows)

    comparison = compare_run_rows_to_simulator_tactical_evidence(rows, simulator)

    assert comparison.matches is True
    assert comparison.differences == ()
    assert comparison.live_length == 1
    assert comparison.simulator_length == 1


def test_env_r5_run_log_entry_point_compares_discard_against_simulator_evidence():
    rows = _rows(action_name=DISCARD_CARDS, before_score=11, after_score=11)
    simulator = successful_tactical_evidence_from_run_rows(rows)

    assert simulator[0].action.name == DISCARD_CARDS
    comparison = compare_run_rows_to_simulator_tactical_evidence(rows, simulator)

    assert comparison.matches is True
    assert comparison.differences == ()


def test_env_r5_run_log_entry_point_reports_simulator_post_state_difference():
    rows = _rows()
    simulator = list(successful_tactical_evidence_from_run_rows(rows))
    simulator[0] = deepcopy(simulator[0])
    simulator[0].after.score += 1

    comparison = compare_run_rows_to_simulator_tactical_evidence(rows, simulator)

    assert comparison.matches is False
    assert comparison.differences == ("step[0].after",)
