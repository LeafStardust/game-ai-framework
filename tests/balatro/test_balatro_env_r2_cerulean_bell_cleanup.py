import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import start_supported_cerulean_bell
from games.balatro.env.boss_draw import clear_cerulean_bell_forced_selection
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _started() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.round = 2
    state.blind = Blind(BlindType.BOSS, requirement=100_000)
    state.boss_name = "Cerulean Bell"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return start_supported_cerulean_bell(
        HeadlessRunState(public=state, seed="TESTSEED")
    )


def test_env_r2_cerulean_bell_cleanup_clears_forced_selection_without_rng():
    run = _started()
    before_rng = run.rng_snapshot()
    assert sum(card.forced_selection for card in run.require_playing_card_order()) == 1

    result = clear_cerulean_bell_forced_selection(run)

    assert all(not card.forced_selection for card in result.require_playing_card_order())
    assert result.rng_snapshot() == before_rng
    assert sum(card.forced_selection for card in run.require_playing_card_order()) == 1


def test_env_r2_cerulean_bell_cleanup_reaches_card_outside_current_hand():
    run = _started()
    forced = next(card for card in run.public.hand if card.forced_selection)
    forced.forced_selection = False
    outside = run.draw_pile[0]
    outside.forced_selection = True

    result = clear_cerulean_bell_forced_selection(run)

    assert all(not card.forced_selection for card in result.require_playing_card_order())
    assert outside.forced_selection


def test_env_r2_cerulean_bell_cleanup_is_idempotent():
    run = _started()
    once = clear_cerulean_bell_forced_selection(run)
    twice = clear_cerulean_bell_forced_selection(once)

    assert all(not card.forced_selection for card in twice.require_playing_card_order())
    assert twice.rng_snapshot() == once.rng_snapshot()


def test_env_r2_cerulean_bell_cleanup_rejects_wrong_boss():
    run = _started()
    run.public.boss_name = "The Wall"

    with pytest.raises(HeadlessTransitionError, match="requires Cerulean Bell"):
        clear_cerulean_bell_forced_selection(run)
