import pytest

from games.balatro.env.blind_progression import BlindProgressionState
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _state() -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    return state


def test_env_r2_headless_run_retains_explicit_blind_progression_state():
    progression = BlindProgressionState(
        small_status="Defeated",
        big_status="Upcoming",
        boss_status="Upcoming",
        blind_on_deck="Big",
        blind_ante=0,
        boss_name="The Hook",
    )

    run = HeadlessRunState(
        public=_state(),
        seed="PROGRESSION",
        blind_progression_state=progression,
    )

    assert run.require_blind_progression_state() is progression
    assert run.blind_progression_state.blind_ante == 0


def test_env_r2_headless_run_does_not_infer_missing_blind_progression():
    state = _state()
    state.ante = -2
    run = HeadlessRunState(public=state, seed="PROGRESSION")

    assert run.blind_progression_state is None
    with pytest.raises(HeadlessTransitionError, match="progression state is unavailable"):
        run.require_blind_progression_state()


def test_env_r2_headless_run_rejects_noncanonical_progression_owner():
    with pytest.raises(HeadlessTransitionError, match="BlindProgressionState or None"):
        HeadlessRunState(
            public=_state(),
            seed="PROGRESSION",
            blind_progression_state={"blind_ante": 1},
        )


def test_env_r2_headless_copy_isolates_retained_blind_progression():
    progression = BlindProgressionState(blind_ante=-1)
    run = HeadlessRunState(
        public=_state(),
        seed="PROGRESSION",
        blind_progression_state=progression,
    )

    copied = run.copy()
    copied.require_blind_progression_state().blind_ante = -2

    assert copied.blind_progression_state is not run.blind_progression_state
    assert copied.require_blind_progression_state().blind_ante == -2
    assert run.require_blind_progression_state().blind_ante == -1


def test_env_r2_headless_run_does_not_impose_false_universal_ante_equality():
    state = _state()
    state.ante = 3
    progression = BlindProgressionState(
        blind_ante=2,
        boss_status="Defeated",
        blind_on_deck="Boss",
    )

    # This exact intermediate exists after Boss end_round has advanced public
    # Ante but before cash-out reset_blinds installs the next blind_ante.  The run
    # container must retain it rather than inventing blind_ante == public ante.
    run = HeadlessRunState(
        public=state,
        seed="PROGRESSION",
        blind_progression_state=progression,
    )

    assert run.public.ante == 3
    assert run.require_blind_progression_state().blind_ante == 2
