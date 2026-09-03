import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import (
    prepare_supported_resource_boss_start,
    start_supported_resource_boss,
)
from games.balatro.env.boss_resources import disable_resource_boss
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.burglar import BurglarJoker
from games.balatro.state import BalatroState


def _run(*, boss_name: str, ante: int = 4) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = ante
    state.round = 8
    state.blind = Blind(BlindType.BOSS, 20000)
    state.boss_name = boss_name
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return HeadlessRunState(public=state, seed="RESOURCE-BOSS")


def test_env_r2_water_stores_post_bonus_discards_then_removes_all_before_jokers():
    run = _run(boss_name="The Water")
    run.round_bonus_discards = 2
    run.round_bonus_hands = 1

    result = prepare_supported_resource_boss_start(run)

    assert result.public.phase == "DRAW_TO_HAND"
    assert result.public.round == 9
    assert result.public.hands_remaining == 5
    assert result.public.discards_remaining == 0
    assert result.boss_discards_sub == 5
    assert result.boss_hands_sub is None
    assert result.round_bonus_hands == 0
    assert result.round_bonus_discards == 0


def test_env_r2_needle_subtracts_reset_hands_minus_one_not_post_bonus_hands():
    run = _run(boss_name="The Needle")
    run.round_bonus_hands = 2
    run.round_bonus_discards = 1

    result = prepare_supported_resource_boss_start(run)

    # Baseline is 6 hands; Needle stores 4 - 1 == 3 and subtracts exactly 3,
    # leaving the two one-shot bonus hands intact on top of the one allowed hand.
    assert result.public.hands_remaining == 3
    assert result.public.discards_remaining == 4
    assert result.boss_hands_sub == 3
    assert result.boss_discards_sub is None
    assert result.round_bonus_hands == 0
    assert result.round_bonus_discards == 0


def test_env_r2_needle_preserves_vanilla_negative_restore_amount_at_zero_reset_hands():
    run = _run(boss_name="The Needle")
    run.public.round_reset_hands = 0

    result = prepare_supported_resource_boss_start(run)

    # Vanilla stores round_resets.hands - 1, so 0 produces -1 and the
    # ease_hands_played(-hands_sub) call adds one to the max(1, ...) baseline.
    assert result.boss_hands_sub == -1
    assert result.public.hands_remaining == 2


def test_env_r2_resource_boss_setting_blind_order_composes_burglar_after_boss_mutation():
    water = _run(boss_name="The Water")
    water.public.jokers = [BurglarJoker()]
    water_result = prepare_supported_resource_boss_start(water)
    assert water_result.boss_discards_sub == 3
    assert water_result.public.discards_remaining == 0
    assert water_result.public.hands_remaining == 7

    needle = _run(boss_name="The Needle")
    needle.public.jokers = [BurglarJoker()]
    needle_result = prepare_supported_resource_boss_start(needle)
    assert needle_result.boss_hands_sub == 3
    assert needle_result.public.hands_remaining == 4
    assert needle_result.public.discards_remaining == 0


def test_env_r2_water_disable_restores_exact_stored_discards_and_clears_private_state():
    started = prepare_supported_resource_boss_start(_run(boss_name="The Water"))

    restored = disable_resource_boss(started)

    assert restored.public.discards_remaining == 3
    assert restored.boss_discards_sub is None
    assert started.public.discards_remaining == 0
    assert started.boss_discards_sub == 3


def test_env_r2_needle_disable_restores_relative_to_current_hands_and_clears_private_state():
    started = prepare_supported_resource_boss_start(_run(boss_name="The Needle"))
    assert started.public.hands_remaining == 1
    started.public.hands_remaining = 0  # one hand was spent before the blind was disabled

    restored = disable_resource_boss(started)

    assert restored.public.hands_remaining == 3
    assert restored.boss_hands_sub is None
    assert started.public.hands_remaining == 0
    assert started.boss_hands_sub == 3


def test_env_r2_resource_boss_disable_requires_matching_active_restore_state():
    with pytest.raises(HeadlessTransitionError, match="stored discards_sub"):
        disable_resource_boss(_run(boss_name="The Water"))

    with pytest.raises(HeadlessTransitionError, match="stored hands_sub"):
        disable_resource_boss(_run(boss_name="The Needle"))

    with pytest.raises(HeadlessTransitionError, match="no audited reversible resource disable"):
        disable_resource_boss(_run(boss_name="The Eye"))


def test_env_r2_resource_boss_start_composes_exact_shuffle_and_deal():
    result = start_supported_resource_boss(_run(boss_name="The Water", ante=4))

    assert result.public.phase == "SELECTING_HAND"
    assert len(result.public.hand) == 8
    assert len(result.draw_pile) == 44
    assert result.boss_discards_sub == 3
    assert result.public.discards_remaining == 0
    assert "nr4" in result.rng.nodes


@pytest.mark.parametrize("boss_name", ["The Wall", "Violet Vessel", "The Eye", "The Mouth", "The Manacle"])
def test_env_r2_resource_boss_gate_rejects_other_bosses(boss_name):
    with pytest.raises(HeadlessTransitionError, match="resource-mutating start set"):
        prepare_supported_resource_boss_start(_run(boss_name=boss_name))


def test_env_r2_resource_boss_start_isolates_input_state_and_private_restore_fields():
    run = _run(boss_name="The Water")
    before_rng = run.rng_snapshot()

    result = prepare_supported_resource_boss_start(run)

    assert result is not run
    assert run.public.phase == "BLIND_SELECT"
    assert run.public.round == 8
    assert run.boss_discards_sub is None
    assert run.rng_snapshot() == before_rng
    assert result.public.phase == "DRAW_TO_HAND"
    assert result.boss_discards_sub == 3
