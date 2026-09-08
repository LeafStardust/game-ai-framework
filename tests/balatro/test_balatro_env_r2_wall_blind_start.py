import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import (
    prepare_supported_wall_blind_start,
    start_supported_wall_blind,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.burglar import BurglarJoker
from games.balatro.state import BalatroState


def _run(seed: str = "WALL") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 2
    state.round = 5
    state.blind = Blind(BlindType.BOSS, 2700)
    state.boss_name = "The Wall"
    state.score = 888
    state.hands_remaining = 1
    state.discards_remaining = 1
    state.discards_used = 2
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return HeadlessRunState(public=state, seed=seed)


def test_env_r2_wall_prepare_uses_authoritative_requirement_and_common_round_lifecycle():
    run = _run()
    run.round_bonus_hands = 1
    run.round_bonus_discards = -2
    before_rng = run.rng_snapshot()

    result = prepare_supported_wall_blind_start(run)

    assert result is not run
    assert run.public.phase == "BLIND_SELECT"
    assert run.public.round == 5
    assert result.public.phase == "DRAW_TO_HAND"
    assert result.public.round == 6
    assert result.public.blind_score == 2700
    assert result.public.boss_name == "The Wall"
    assert result.public.hands_remaining == 5
    assert result.public.discards_remaining == 1
    assert result.public.discards_used == 0
    assert result.public.score == 0
    assert result.round_bonus_hands == 0
    assert result.round_bonus_discards == 0
    assert result.rng_snapshot() == before_rng


def test_env_r2_wall_setting_blind_applies_burglar_before_exact_deal():
    run = _run()
    run.public.jokers = [BurglarJoker()]

    result = start_supported_wall_blind(run)

    assert result.public.phase == "SELECTING_HAND"
    assert result.public.round == 6
    assert result.public.blind_score == 2700
    assert result.public.hands_remaining == 7
    assert result.public.discards_remaining == 0
    assert len(result.public.hand) == 8
    assert len(result.draw_pile) == 44
    assert "nr2" in result.rng.nodes


def test_env_r2_wall_start_clears_nonapplicable_mutable_boss_state():
    run = _run()
    run.public.boss_blind_state_observed = True
    run.public.boss_blind_hands = {"PAIR"}
    run.public.boss_blind_only_hand = "FLUSH"

    result = prepare_supported_wall_blind_start(run)

    assert result.public.boss_blind_state_observed is False
    assert result.public.boss_blind_hands == set()
    assert result.public.boss_blind_only_hand is None


def test_env_r2_wall_start_fails_closed_on_wrong_or_missing_boss_identity():
    run = _run()
    run.public.boss_name = "The Needle"
    with pytest.raises(HeadlessTransitionError, match="authoritative boss name"):
        prepare_supported_wall_blind_start(run)

    run = _run()
    run.public.blind = Blind(BlindType.BIG, 2700)
    with pytest.raises(HeadlessTransitionError, match="Boss Blind"):
        prepare_supported_wall_blind_start(run)


def test_env_r2_wall_start_keeps_unowned_tag_and_voucher_surfaces_blocked():
    run = _run()
    run.tags.append("DOUBLE")
    with pytest.raises(HeadlessTransitionError, match="active tags"):
        prepare_supported_wall_blind_start(run)

    run = _run()
    run.public.vouchers.append("Grabber")
    with pytest.raises(HeadlessTransitionError, match="vouchers"):
        prepare_supported_wall_blind_start(run)
