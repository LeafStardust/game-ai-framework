from math import ceil

import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import start_supported_start_inert_boss
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


def _flint_run(
    *,
    seed="R4-FLINT",
    level=2,
    requirement=99_999,
    hands_remaining=4,
):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 2
    state.round = 6
    state.blind = Blind(BlindType.BOSS, requirement=requirement, reward=5)
    state.boss_name = "The Flint"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    state.hands_remaining = hands_remaining
    state.hand_levels["HIGH_CARD"] = level
    state.vouchers = ["v_paint_brush"]
    state.vouchers_observed = True
    state.hand_size = 9
    run = start_supported_start_inert_boss(
        HeadlessRunState(public=state, seed=seed)
    )
    run.public.hands_remaining = hands_remaining
    return run


def _flint_high_card_score(card, level):
    base_chips = 5 + 10 * (level - 1)
    base_mult = 1 + (level - 1)
    return (
        ceil(base_chips / 2) + BalatroScorer.RANK_CHIPS[card.rank]
    ) * ceil(base_mult / 2)


def test_env_r4_flint_play_uses_canonical_base_transform_and_preserves_input():
    run = _flint_run()
    selected = run.public.hand[0]
    before_hand = list(run.public.hand)
    before_rng = run.rng_snapshot()

    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.score == _flint_high_card_score(selected, 2)
    assert result.public.phase == "SELECTING_HAND"
    assert result.public.hands_remaining == 3
    assert len(result.public.hand) == result.public.hand_size == 9
    assert result.rng_snapshot() == before_rng
    assert run.public.score == 0
    assert run.public.hands_remaining == 4
    assert run.public.hand == before_hand
    assert run.public.discard_pile == []


def test_env_r4_flint_play_clear_stops_at_round_eval_without_redraw():
    run = _flint_run(seed="R4-FLINT-CLEAR", requirement=1)

    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.phase == "ROUND_EVAL"
    assert result.public.score >= result.public.blind.requirement
    assert result.public.hands_remaining == 3
    assert len(result.public.hand) == 8
    assert len(result.draw_pile) == 43


def test_env_r4_flint_play_final_hand_loss_stops_without_redraw():
    run = _flint_run(
        seed="R4-FLINT-LOSS",
        requirement=99_999,
        hands_remaining=1,
    )

    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.phase == "GAME_OVER"
    assert result.public.score < result.public.blind.requirement
    assert result.public.hands_remaining == 0
    assert len(result.public.hand) == 8
    assert len(result.draw_pile) == 43


def test_env_r4_flint_play_rejects_unowned_callbacks_atomically():
    run = _flint_run(seed="R4-FLINT-UNSUPPORTED")
    joker = object()
    run.public.jokers = [joker]
    before_hand = list(run.public.hand)
    before_rng = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="Joker callbacks"):
        apply_supported_ordinary_play(run, (0,))

    assert run.public.jokers == [joker]
    assert run.public.hand == before_hand
    assert run.public.score == 0
    assert run.public.hands_remaining == 4
    assert run.rng_snapshot() == before_rng
