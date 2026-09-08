import pytest

from games.balatro.env.rng import BalatroRNG
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _state() -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    return state


def test_env_r2_headless_state_creates_exact_rng_owner_from_seed():
    run = HeadlessRunState(public=_state(), seed="TESTSEED")

    assert isinstance(run.rng, BalatroRNG)
    assert run.rng.seed == "TESTSEED"
    assert run.rng.random("shuffle1") == 0.3203278531352878


def test_env_r2_headless_state_restores_rng_snapshot_exactly():
    source = BalatroRNG("TESTSEED")
    source.random("shuffle1")
    snapshot = source.snapshot()

    run = HeadlessRunState(
        public=_state(),
        seed="TESTSEED",
        rng_state=snapshot,
    )

    assert run.rng_snapshot() == snapshot
    assert run.rng.random("shuffle1") == source.random("shuffle1")


def test_env_r2_headless_state_rejects_rng_snapshot_for_different_seed():
    snapshot = BalatroRNG("OTHER").snapshot()

    with pytest.raises(HeadlessTransitionError, match="seed does not match"):
        HeadlessRunState(public=_state(), seed="TESTSEED", rng_state=snapshot)


def test_env_r2_headless_state_rejects_invalid_rng_snapshot():
    with pytest.raises(HeadlessTransitionError, match="invalid Balatro RNG snapshot"):
        HeadlessRunState(public=_state(), seed="TESTSEED", rng_state={})


def test_env_r2_headless_state_rejects_arbitrary_rng_placeholder():
    with pytest.raises(HeadlessTransitionError, match="rng_state must be BalatroRNG"):
        HeadlessRunState(public=_state(), seed="TESTSEED", rng_state=object())


def test_env_r2_headless_copy_isolates_rng_queue_progress():
    run = HeadlessRunState(public=_state(), seed="TESTSEED")
    copied = run.copy()

    assert copied.rng is not run.rng
    assert copied.rng_snapshot() == run.rng_snapshot()

    copied_value = copied.rng.random("shuffle1")
    assert copied_value == 0.3203278531352878
    assert "shuffle1" not in run.rng.nodes
