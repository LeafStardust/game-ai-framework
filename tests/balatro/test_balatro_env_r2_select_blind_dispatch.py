import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.boss_selection import BOSS_KEY_BY_NAME
from games.balatro.env.select_blind import (
    SUPPORTED_SELECT_BLIND_BOSS_NAMES,
    can_select_blind_exact,
    select_blind_exact,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _nonboss_run() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.blind = Blind(BlindType.SMALL, requirement=300)
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return HeadlessRunState(public=state, seed="SELECT-BLIND")


def _boss_run(name: str) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.blind = Blind(BlindType.BOSS, requirement=600)
    state.boss_name = name
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return HeadlessRunState(public=state, seed="SELECT-BLIND-BOSS")


def test_env_r2_select_blind_dispatch_covers_every_vanilla_boss_identity():
    assert SUPPORTED_SELECT_BLIND_BOSS_NAMES == frozenset(BOSS_KEY_BY_NAME)
    assert len(SUPPORTED_SELECT_BLIND_BOSS_NAMES) == 28


def test_env_r2_select_blind_nonboss_legality_is_exact_and_nonmutating():
    run = _nonboss_run()
    before_rng = run.rng_snapshot()
    before_phase = run.public.phase
    before_round = run.public.round

    assert can_select_blind_exact(run)

    assert run.public.phase == before_phase
    assert run.public.round == before_round
    assert run.rng_snapshot() == before_rng


def test_env_r2_select_blind_executes_existing_nonboss_lifecycle_and_deal():
    run = _nonboss_run()

    result = select_blind_exact(run)

    assert result.public.phase == "SELECTING_HAND"
    assert result.public.round == run.public.round + 1
    assert len(result.public.hand) == result.public.hand_size
    assert len(result.draw_pile) == len(result.public.deck)
    assert run.public.phase == "BLIND_SELECT"
    assert run.public.hand == []


def test_env_r2_select_blind_routes_audited_facing_boss_start():
    run = _boss_run("The House")

    result = select_blind_exact(run)

    assert result.public.phase == "SELECTING_HAND"
    assert result.public.boss_name == "The House"
    assert result.public.hand
    assert all(card.facing_observed for card in result.public.hand)
    assert all(card.face_down for card in result.public.hand)


def test_env_r2_select_blind_fails_closed_for_unknown_boss_identity():
    run = _boss_run("Not A Vanilla Boss")

    assert not can_select_blind_exact(run)
    with pytest.raises(HeadlessTransitionError, match="unsupported SELECT_BLIND Boss"):
        select_blind_exact(run)


def test_env_r2_select_blind_fails_closed_when_active_tags_are_unowned():
    run = _nonboss_run()
    run.tags = ["tag_double"]

    assert not can_select_blind_exact(run)
    with pytest.raises(HeadlessTransitionError, match="active tags"):
        select_blind_exact(run)


def test_env_r2_select_blind_fails_closed_for_inexact_voucher_history():
    run = _nonboss_run()
    run.public.vouchers = ["v_unknown"]
    run.public.vouchers_observed = True

    assert not can_select_blind_exact(run)
    with pytest.raises(HeadlessTransitionError, match="exact supported vouchers"):
        select_blind_exact(run)


def test_env_r2_select_blind_rejects_non_run_input():
    with pytest.raises(TypeError, match="HeadlessRunState"):
        can_select_blind_exact(object())
    with pytest.raises(TypeError, match="HeadlessRunState"):
        select_blind_exact(object())
