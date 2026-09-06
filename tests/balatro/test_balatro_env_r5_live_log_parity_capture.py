import pytest

from games.balatro.actions import PLAY_CARDS
from games.balatro.live.parity_capture import successful_tactical_evidence_from_run_rows


def _state(*, sequence, score, hand):
    return {
        "sequence": sequence,
        "phase": "SELECTING_HAND",
        "state_complete": True,
        "payload": {
            "score": score,
            "round": {"hands_left": 4, "discards_left": 3, "chips": 300},
            "hand": {
                "limit": len(hand),
                "cards": [
                    {"id": f"card-{index}", "value": {"rank": rank, "suit": suit}}
                    for index, (rank, suit) in enumerate(hand)
                ],
            },
            "cards": {"cards": []},
        },
    }


def _rows(*, result_action=None):
    action = {"name": PLAY_CARDS, "indices": [0]}
    return [
        {"event": "observation", "data": {"state": _state(sequence=10, score=0, hand=[("A", "S"), ("K", "H")])}},
        {"event": "bond_build", "data": {"diagnostic": True}},
        {"event": "decision", "data": {"action": action, "rationale": {}}},
        {
            "event": "action_result",
            "data": {
                "action": result_action or action,
                "success": True,
                "state": _state(sequence=11, score=11, hand=[("K", "H")]),
            },
        },
    ]


def test_env_r5_extracts_successful_tactical_evidence_from_existing_run_log_shape():
    evidence = successful_tactical_evidence_from_run_rows(_rows())

    assert len(evidence) == 1
    transition = evidence[0]
    assert transition.before.score == 0
    assert transition.after.score == 11
    assert transition.action.name == PLAY_CARDS
    assert transition.selected_hand_indices == (0,)
    assert transition.action.cards == [transition.before.hand[0]]
    assert transition.before.hand[0].rank == "A"
    assert transition.before.hand[0].suit == "Spades"


def test_env_r5_ignores_non_tactical_successful_run_log_actions():
    rows = [
        {"event": "observation", "data": {"state": _state(sequence=1, score=0, hand=[("A", "S")])}},
        {"event": "decision", "data": {"action": {"name": "SELECT_BLIND"}}},
        {
            "event": "action_result",
            "data": {
                "action": {"name": "SELECT_BLIND"},
                "success": True,
                "state": _state(sequence=2, score=0, hand=[("A", "S")]),
            },
        },
    ]

    assert successful_tactical_evidence_from_run_rows(rows) == ()


def test_env_r5_fails_closed_when_successful_result_does_not_match_decision():
    with pytest.raises(ValueError, match="does not match captured decision"):
        successful_tactical_evidence_from_run_rows(
            _rows(result_action={"name": PLAY_CARDS, "indices": [1]})
        )


def test_env_r5_fails_closed_on_invalid_logged_hand_index():
    rows = _rows()
    rows[2]["data"]["action"] = {"name": PLAY_CARDS, "indices": [7]}
    rows[3]["data"]["action"] = {"name": PLAY_CARDS, "indices": [7]}

    with pytest.raises(ValueError, match="outside the translated public hand"):
        successful_tactical_evidence_from_run_rows(rows)
