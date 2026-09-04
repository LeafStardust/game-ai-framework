import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import (
    _REQUIREMENT_ONLY_BOSS_NAMES,
    _START_INERT_BOSS_NAMES,
    prepare_supported_requirement_only_boss_start,
    prepare_supported_start_inert_boss_start,
    start_supported_start_inert_boss,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


START_INERT_BOSSES = ("The Psychic", "The Flint", "The Tooth", "The Hook", "The Ox")


def _run(boss_name: str) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 4
    state.round = 6
    state.blind = Blind(BlindType.BOSS, requirement=20000)
    state.boss_name = boss_name
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    state.hands_remaining = 1
    state.discards_remaining = 1
    return HeadlessRunState(public=state, seed="STARTINERT")


@pytest.mark.parametrize("boss_name", START_INERT_BOSSES)
def test_env_r2_start_inert_boss_predeal_owns_only_common_start_lifecycle(boss_name):
    run = _run(boss_name)
    before_rng = run.rng_snapshot()

    result = prepare_supported_start_inert_boss_start(run)

    assert result is not run
    assert run.public.phase == "BLIND_SELECT"
    assert run.public.round == 6
    assert run.public.hands_remaining == 1
    assert run.public.discards_remaining == 1
    assert run.rng_snapshot() == before_rng

    assert result.public.phase == "DRAW_TO_HAND"
    assert result.public.round == 7
    assert result.public.blind_score == 20000
    assert result.public.hands_remaining == 4
    assert result.public.discards_remaining == 3
    assert result.public.hand_size == run.public.hand_size
    assert result.public.boss_blind_state_observed is False
    assert result.rng_snapshot() == before_rng


@pytest.mark.parametrize("boss_name", START_INERT_BOSSES)
def test_env_r2_start_inert_boss_composes_with_exact_shuffle_and_deal(boss_name):
    result = start_supported_start_inert_boss(_run(boss_name))

    assert result.public.phase == "SELECTING_HAND"
    assert result.public.round == 7
    assert result.public.hands_remaining == 4
    assert result.public.discards_remaining == 3
    assert len(result.public.hand) == result.public.hand_size
    assert len(result.draw_pile) == 52 - result.public.hand_size
    assert result.rng.nodes["nr4"] != 0


def test_env_r2_start_inert_boss_set_is_semantically_distinct_from_requirement_only():
    assert _START_INERT_BOSS_NAMES == frozenset(START_INERT_BOSSES)
    assert _START_INERT_BOSS_NAMES.isdisjoint(_REQUIREMENT_ONLY_BOSS_NAMES)

    with pytest.raises(HeadlessTransitionError, match="requirement-only"):
        prepare_supported_requirement_only_boss_start(_run("The Psychic"))


def test_env_r2_start_inert_boss_helper_rejects_unclassified_bosses():
    with pytest.raises(HeadlessTransitionError, match="start-inert"):
        prepare_supported_start_inert_boss_start(_run("The Wall"))

    with pytest.raises(HeadlessTransitionError, match="start-inert"):
        prepare_supported_start_inert_boss_start(_run("Unknown Boss"))
