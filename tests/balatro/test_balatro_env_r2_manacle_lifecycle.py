import pytest

from games.balatro.blinds.boss import BossBlind
from games.balatro.env.blind_start import (
    prepare_supported_resource_boss_start,
    start_supported_resource_boss,
)
from games.balatro.env.boss_resources import (
    apply_resource_boss_start,
    disable_resource_boss,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run(*, hand_size: int = 8) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 1
    state.round = 0
    state.boss_name = "The Manacle"
    state.blind = BossBlind(requirement=600, name="THE_MANACLE")
    state.hand_size = hand_size
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return HeadlessRunState(public=state, seed="MANACLE")


def test_env_r2_manacle_direct_start_stores_and_removes_one_hand_size_slot():
    run = _run()

    result = apply_resource_boss_start(run)

    assert result is not run
    assert run.public.hand_size == 8
    assert run.boss_hand_size_sub is None
    assert result.public.hand_size == 7
    assert result.boss_hand_size_sub == 1


def test_env_r2_manacle_disable_restores_exact_stored_hand_size_slot():
    active = apply_resource_boss_start(_run())

    result = disable_resource_boss(active)

    assert active.public.hand_size == 7
    assert active.boss_hand_size_sub == 1
    assert result.public.hand_size == 8
    assert result.boss_hand_size_sub is None


def test_env_r2_manacle_start_and_disable_fail_closed_on_invalid_lifecycle_state():
    run = _run()
    run.public.hand_size = 0
    with pytest.raises(HeadlessTransitionError, match="positive current hand size"):
        apply_resource_boss_start(run)

    with pytest.raises(HeadlessTransitionError, match="stored hand_size_sub"):
        disable_resource_boss(_run())

    active = apply_resource_boss_start(_run())
    with pytest.raises(HeadlessTransitionError, match="already active"):
        apply_resource_boss_start(active)


def test_env_r2_manacle_predeal_applies_after_round_resource_baseline():
    run = _run()
    run.public.hands_remaining = 99
    run.public.discards_remaining = 99

    prepared = prepare_supported_resource_boss_start(run)

    assert prepared.public.round == 1
    assert prepared.public.hands_remaining == 4
    assert prepared.public.discards_remaining == 3
    assert prepared.public.hand_size == 7
    assert prepared.boss_hand_size_sub == 1
    assert prepared.public.phase == "DRAW_TO_HAND"


def test_env_r2_manacle_full_start_deals_reduced_seven_card_hand():
    run = _run()

    result = start_supported_resource_boss(run)

    assert result.public.phase == "SELECTING_HAND"
    assert result.public.hand_size == 7
    assert len(result.public.hand) == 7
    assert len(result.draw_pile) == 45
    assert len(result.public.deck) == 45
    assert result.boss_hand_size_sub == 1


def test_env_r2_manacle_full_start_isolates_input_state_and_rng():
    run = _run()
    before_rng = run.rng_snapshot()

    result = start_supported_resource_boss(run)

    assert result is not run
    assert run.public.phase == "BLIND_SELECT"
    assert run.public.round == 0
    assert run.public.hand_size == 8
    assert run.public.hand == []
    assert run.boss_hand_size_sub is None
    assert run.rng_snapshot() == before_rng
    assert result.rng_snapshot() != before_rng
