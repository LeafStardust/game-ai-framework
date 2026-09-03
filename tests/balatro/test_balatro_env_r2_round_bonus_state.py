import pytest

from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _state() -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    return state


def test_env_r2_round_bonus_state_accepts_signed_exact_integers_and_copies():
    run = HeadlessRunState(
        public=_state(),
        seed="BONUS",
        round_bonus_hands=-2,
        round_bonus_discards=3,
    )

    copied = run.copy()

    assert copied.round_bonus_hands == -2
    assert copied.round_bonus_discards == 3
    copied.round_bonus_hands = 7
    assert run.round_bonus_hands == -2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("round_bonus_hands", True),
        ("round_bonus_hands", 1.0),
        ("round_bonus_hands", "1"),
        ("round_bonus_discards", False),
        ("round_bonus_discards", 2.0),
        ("round_bonus_discards", "2"),
    ],
)
def test_env_r2_round_bonus_state_rejects_non_exact_integers(field, value):
    kwargs = {field: value}

    with pytest.raises(HeadlessTransitionError, match=field):
        HeadlessRunState(public=_state(), seed="BONUS", **kwargs)
