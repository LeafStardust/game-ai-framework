import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.crimson_heart import (
    prepare_supported_crimson_heart_start,
    start_supported_crimson_heart,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.turtle_bean import TurtleBeanJoker
from games.balatro.state import BalatroState


def _run(*, joker_count: int = 1, seed: str = "CRIMSONSTART") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.round = 2
    state.blind = Blind(BlindType.BOSS, requirement=100_000)
    state.boss_name = "Crimson Heart"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    for index in range(joker_count):
        joker = FlatMultJoker(index + 1)
        joker.live_id = 200 + index
        state.jokers.append(joker)
    return HeadlessRunState(public=state, seed=seed)


def test_env_r2_crimson_prepare_sets_prepped_before_draw_without_consuming_crimson_rng():
    run = _run(joker_count=2)

    result = prepare_supported_crimson_heart_start(run)

    assert result.public.round == 3
    assert result.public.blind_score == 100_000
    assert result.public.hands_remaining == 4
    assert result.public.discards_remaining == 3
    assert result.public.phase == "DRAW_TO_HAND"
    assert getattr(result.public.blind, "prepped") is True
    assert "crimson_heart" not in result.rng.nodes
    assert not hasattr(run.public.blind, "prepped")


def test_env_r2_crimson_full_start_deals_then_debuffs_exactly_one_joker():
    result = start_supported_crimson_heart(_run(joker_count=3))

    assert result.public.phase == "SELECTING_HAND"
    assert len(result.public.hand) == 8
    assert len(result.draw_pile) == 44
    assert sum(bool(getattr(joker, "debuffed", False)) for joker in result.public.jokers) == 1
    assert getattr(result.public.blind, "prepped") is False
    assert "nr1" in result.rng.nodes
    assert "crimson_heart" in result.rng.nodes


def test_env_r2_crimson_full_start_with_no_jokers_consumes_no_crimson_rng():
    result = start_supported_crimson_heart(_run(joker_count=0))

    assert result.public.phase == "SELECTING_HAND"
    assert result.public.jokers == []
    assert getattr(result.public.blind, "prepped") is False
    assert "crimson_heart" not in result.rng.nodes


def test_env_r2_crimson_start_isolates_input_state_and_rng():
    run = _run(joker_count=2)
    before = run.rng_snapshot()

    result = start_supported_crimson_heart(run)

    assert run.public.phase == "BLIND_SELECT"
    assert run.public.hand == []
    assert all(not bool(getattr(joker, "debuffed", False)) for joker in run.public.jokers)
    assert run.rng_snapshot() == before
    assert result.rng_snapshot() != before


def test_env_r2_crimson_start_keeps_unclassified_setting_blind_jokers_fail_closed():
    run = _run(joker_count=0)
    run.public.jokers = [TurtleBeanJoker()]

    with pytest.raises(HeadlessTransitionError, match="unsupported identity"):
        start_supported_crimson_heart(run)


def test_env_r2_crimson_start_rejects_wrong_boss_and_disabled_blind():
    run = _run()
    run.public.boss_name = "The Wall"
    with pytest.raises(HeadlessTransitionError, match="requires Crimson Heart"):
        prepare_supported_crimson_heart_start(run)

    run = _run()
    run.public.blind.disabled = True
    with pytest.raises(HeadlessTransitionError, match="active blind"):
        prepare_supported_crimson_heart_start(run)
