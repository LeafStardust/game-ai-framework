import pytest

from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _state(*, boss_name: str = "The Manacle") -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.boss_name = boss_name
    return state


def test_env_r2_manacle_hand_size_sub_accepts_exact_nonnegative_integer():
    run = HeadlessRunState(
        public=_state(),
        seed="MANACLE",
        boss_hand_size_sub=1,
    )

    assert run.boss_hand_size_sub == 1


@pytest.mark.parametrize("value", [True, "1", 1.0, -1])
def test_env_r2_manacle_hand_size_sub_rejects_nonexact_or_negative_values(value):
    with pytest.raises(HeadlessTransitionError, match="boss_hand_size_sub"):
        HeadlessRunState(
            public=_state(),
            seed="MANACLE",
            boss_hand_size_sub=value,
        )


def test_env_r2_manacle_hand_size_sub_is_bound_to_manacle_identity():
    with pytest.raises(HeadlessTransitionError, match="only valid for The Manacle"):
        HeadlessRunState(
            public=_state(boss_name="The Water"),
            seed="MANACLE",
            boss_hand_size_sub=1,
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"boss_hands_sub": 1, "boss_hand_size_sub": 1},
        {"boss_discards_sub": 1, "boss_hand_size_sub": 1},
    ],
)
def test_env_r2_reversible_boss_resource_adjustments_are_mutually_exclusive(kwargs):
    state = _state()
    # Bind the other field to its own Boss long enough to prove the global
    # exclusivity check independently of identity validation.
    if "boss_hands_sub" in kwargs:
        state.boss_name = "The Needle"
        with pytest.raises(HeadlessTransitionError):
            HeadlessRunState(public=state, seed="MANACLE", **kwargs)
    else:
        state.boss_name = "The Water"
        with pytest.raises(HeadlessTransitionError):
            HeadlessRunState(public=state, seed="MANACLE", **kwargs)


def test_env_r2_manacle_private_state_survives_isolated_copy():
    run = HeadlessRunState(
        public=_state(),
        seed="MANACLE",
        boss_hand_size_sub=1,
    )

    copied = run.copy()

    assert copied is not run
    assert copied.public is not run.public
    assert copied.boss_hand_size_sub == 1
