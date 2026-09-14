import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import start_supported_verdant_leaf
from games.balatro.env.boss_defeat import defeat_supported_boss
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.serialization import (
    restore_headless_run_state,
    serialize_headless_run_state,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _verdant_run(*, requirement=1):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 8
    state.round = 20
    state.blind = Blind(BlindType.BOSS, requirement=requirement, reward=8)
    state.boss_name = "Verdant Leaf"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return start_supported_verdant_leaf(
        HeadlessRunState(public=state, seed="R4-VERDANT")
    )


def test_env_r4_verdant_scores_without_debuffed_card_chips_and_cleans_on_defeat():
    run = _verdant_run()
    snapshot = serialize_headless_run_state(run)
    restored = restore_headless_run_state(snapshot)

    result = apply_supported_ordinary_play(restored, (0,))
    defeated = defeat_supported_boss(result)

    assert all(card.debuffed for card in restored.require_playing_card_order())
    assert result.public.phase == "ROUND_EVAL"
    assert result.public.score == 5
    assert all(card.debuffed for card in result.require_playing_card_order())
    assert not any(card.debuffed for card in defeated.require_playing_card_order())
    assert serialize_headless_run_state(run) == snapshot


def test_env_r4_verdant_rejects_incomplete_all_card_debuff_atomically():
    run = _verdant_run(requirement=99_999)
    run.public.hand[0].debuffed = False
    before = serialize_headless_run_state(run)

    with pytest.raises(HeadlessTransitionError, match="all-card debuff state"):
        apply_supported_ordinary_play(run, (0,))

    assert serialize_headless_run_state(run) == before
