import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.select_blind import select_blind_exact
from games.balatro.env.serialization import serialize_headless_run_state
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run(name: str, *, ante: int, requirement: int) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = ante
    state.round = 2
    state.blind = Blind(BlindType.BOSS, requirement, reward=5)
    state.boss_name = name
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return select_blind_exact(
        HeadlessRunState(public=state, seed=f"R4-REQUIREMENT-{name}")
    )


@pytest.mark.parametrize(
    ("name", "ante", "requirement"),
    (("The Wall", 2, 3_200), ("Violet Vessel", 8, 300_000)),
)
def test_env_r4_requirement_only_boss_play_preserves_exact_inflated_target(
    name,
    ante,
    requirement,
):
    run = _run(name, ante=ante, requirement=requirement)
    before_rng = run.rng_snapshot()

    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.blind.requirement == requirement
    assert result.public.blind_score == requirement
    assert result.public.score > 0
    assert result.public.hands_remaining == 3
    assert result.public.phase == "SELECTING_HAND"
    assert len(result.public.hand) == result.public.hand_size == 8
    assert result.rng_snapshot() == before_rng
    assert run.public.score == 0
    assert run.public.hands_remaining == 4


@pytest.mark.parametrize(
    "mutate",
    (
        lambda run: setattr(run.public.blind, "requirement", 1_600),
        lambda run: setattr(run.public, "blind_score", 1_600),
        lambda run: setattr(run, "boss_hands_sub", 0),
        lambda run: setattr(run, "boss_discards_sub", 0),
        lambda run: setattr(run, "boss_hand_size_sub", 0),
    ),
)
def test_env_r4_requirement_only_boss_play_rejects_inexact_target_atomically(mutate):
    run = _run("The Wall", ante=2, requirement=3_200)
    mutate(run)
    before = serialize_headless_run_state(run)

    with pytest.raises(
        HeadlessTransitionError,
        match="requires its exact active target state",
    ):
        apply_supported_ordinary_play(run, (0,))

    assert serialize_headless_run_state(run) == before
