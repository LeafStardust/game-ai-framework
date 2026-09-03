import pytest

from games.balatro.blinds.blind import create_small_blind
from games.balatro.env.blind_start import (
    prepare_pristine_first_small_blind,
    start_pristine_first_small_blind,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.burglar import BurglarJoker
from games.balatro.state import BalatroState


def _run(seed: str = "TESTSEED") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 1
    state.round = 0
    state.blind = create_small_blind(300)
    state.score = 123
    state.blind_score = 999
    state.hands_remaining = 0
    state.discards_remaining = 0
    state.discards_used = None
    state.last_played_hand = "PAIR"
    state.round_hand_play_counts["PAIR"] = 2
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return HeadlessRunState(public=state, seed=seed)


def test_env_r2_first_blind_prepare_resets_round_state_before_draw():
    run = _run()

    result = prepare_pristine_first_small_blind(run)

    assert result is not run
    assert run.public.phase == "BLIND_SELECT"
    assert run.public.round == 0
    assert run.public.score == 123
    assert result.public.phase == "DRAW_TO_HAND"
    assert result.public.round == 1
    assert result.public.score == 0
    assert result.public.blind_score == 300
    assert result.public.hands_remaining == 4
    assert result.public.discards_remaining == 3
    assert result.public.discards_used == 0
    assert result.public.last_played_hand is None
    assert all(value == 0 for value in result.public.round_hand_play_counts.values())
    assert result.rng_snapshot() == run.rng_snapshot()


def test_env_r2_first_blind_start_composes_lifecycle_shuffle_and_initial_draw():
    result = start_pristine_first_small_blind(_run())

    assert result.public.phase == "SELECTING_HAND"
    assert result.public.round == 1
    assert result.public.blind_score == 300
    assert result.public.hands_remaining == 4
    assert result.public.discards_remaining == 3
    assert len(result.public.hand) == 8
    assert len(result.draw_pile) == 44
    assert result.rng.nodes["nr1"] == 0.8232194488594


def test_env_r2_first_blind_start_fails_closed_without_authoritative_allowances():
    run = _run()
    run.public.round_reset_hands_observed = False
    with pytest.raises(HeadlessTransitionError, match="authoritative round-reset"):
        prepare_pristine_first_small_blind(run)

    run = _run()
    run.public.round_reset_discards_observed = False
    with pytest.raises(HeadlessTransitionError, match="authoritative round-reset"):
        prepare_pristine_first_small_blind(run)


def test_env_r2_first_blind_start_fails_closed_on_nonvanilla_reset_allowances():
    run = _run()
    run.public.round_reset_hands = 5
    with pytest.raises(HeadlessTransitionError, match="4-hand/3-discard"):
        prepare_pristine_first_small_blind(run)

    run = _run()
    run.public.round_reset_discards = 4
    with pytest.raises(HeadlessTransitionError, match="4-hand/3-discard"):
        prepare_pristine_first_small_blind(run)


def test_env_r2_first_blind_start_requires_zero_pending_round_bonuses():
    run = _run()
    run.round_bonus_hands = 1
    with pytest.raises(HeadlessTransitionError, match="zero pending round bonuses"):
        prepare_pristine_first_small_blind(run)

    run = _run()
    run.round_bonus_discards = -1
    with pytest.raises(HeadlessTransitionError, match="zero pending round bonuses"):
        prepare_pristine_first_small_blind(run)


def test_env_r2_first_blind_start_rejects_any_acquired_modifier_surface():
    run = _run()
    run.public.jokers.append(BurglarJoker())
    with pytest.raises(HeadlessTransitionError, match="no acquired run modifiers"):
        prepare_pristine_first_small_blind(run)

    run = _run()
    run.tags.append("DOUBLE")
    with pytest.raises(HeadlessTransitionError, match="no acquired run modifiers"):
        prepare_pristine_first_small_blind(run)


def test_env_r2_first_blind_start_rejects_wrong_phase_round_or_blind():
    run = _run()
    run.public.phase = "SHOP"
    with pytest.raises(HeadlessTransitionError, match="BLIND_SELECT"):
        prepare_pristine_first_small_blind(run)

    run = _run()
    run.public.round = 1
    with pytest.raises(HeadlessTransitionError, match="ante 1 round 0"):
        prepare_pristine_first_small_blind(run)

    run = _run()
    run.public.blind = None
    with pytest.raises(HeadlessTransitionError, match="Small Blind"):
        prepare_pristine_first_small_blind(run)
