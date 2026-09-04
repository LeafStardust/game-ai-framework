import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import (
    prepare_supported_amber_acorn_start,
    prepare_supported_nonboss_blind_start,
    prepare_supported_requirement_only_boss_start,
    prepare_supported_resource_boss_start,
)
from games.balatro.env.boss_disable import disable_supported_boss
from games.balatro.env.crimson_heart import prepare_supported_crimson_heart_start
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.burglar import BurglarJoker
from games.balatro.jokers.chicot import ChicotJoker
from games.balatro.state import BalatroState


def _run(
    *,
    boss_name: str | None,
    blind_type: BlindType = BlindType.BOSS,
    requirement: int = 20000,
) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 4
    state.round = 8
    state.blind = Blind(blind_type, requirement)
    state.boss_name = boss_name
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return HeadlessRunState(public=state, seed="CHICOT")


def test_env_r2_chicot_water_disable_runs_after_burglar_setting_blind_effect():
    run = _run(boss_name="The Water")
    run.public.jokers = [BurglarJoker(), ChicotJoker()]

    result = prepare_supported_resource_boss_start(run)

    # Water first removes all three baseline discards. Burglar then adds three
    # hands and sets current discards to zero. Chicot's queued disable runs only
    # after the full Joker pass and restores Water's stored three discards.
    assert result.public.hands_remaining == 7
    assert result.public.discards_remaining == 3
    assert result.boss_discards_sub is None
    assert result.public.blind.disabled is True

    # Input isolation is required even though the composed output is disabled.
    assert run.public.hands_remaining == 4
    assert run.public.discards_remaining == 3
    assert not getattr(run.public.blind, "disabled", False)


def test_env_r2_chicot_needle_restores_source_stored_hands_before_draw_phase():
    run = _run(boss_name="The Needle")
    run.public.jokers = [ChicotJoker()]

    result = prepare_supported_resource_boss_start(run)

    assert result.public.hands_remaining == 4
    assert result.boss_hands_sub is None
    assert result.public.blind.disabled is True
    assert result.public.phase == "DRAW_TO_HAND"


@pytest.mark.parametrize(
    ("boss_name", "inflated_requirement", "restored_requirement"),
    [
        ("The Wall", 40000, 20000),
        ("Violet Vessel", 60000, 20000),
    ],
)
def test_env_r2_chicot_restores_requirement_only_boss_target(
    boss_name: str,
    inflated_requirement: int,
    restored_requirement: int,
):
    run = _run(boss_name=boss_name, requirement=inflated_requirement)
    run.public.jokers = [ChicotJoker()]

    result = prepare_supported_requirement_only_boss_start(run)

    assert result.public.blind.disabled is True
    assert result.public.blind.requirement == restored_requirement
    assert result.public.blind_score == restored_requirement
    assert result.public.phase == "DRAW_TO_HAND"
    assert run.public.blind.requirement == inflated_requirement
    assert run.public.blind_score == 0


def test_env_r2_requirement_boss_disable_rejects_unsynchronized_or_nondivisible_target():
    run = _run(boss_name="The Wall", requirement=40000)
    run.public.blind_score = 39999
    with pytest.raises(
        HeadlessTransitionError,
        match="synchronized active target state",
    ):
        disable_supported_boss(run, pre_deal=True)

    run = _run(boss_name="Violet Vessel", requirement=40001)
    run.public.blind_score = 40001
    with pytest.raises(
        HeadlessTransitionError,
        match="not exactly divisible",
    ):
        disable_supported_boss(run, pre_deal=True)


def test_env_r2_chicot_predeal_manacle_fails_closed_without_prior_physical_deck_order():
    run = _run(boss_name="The Manacle")
    run.public.jokers = [ChicotJoker()]
    original_hand_size = run.public.hand_size

    with pytest.raises(
        HeadlessTransitionError,
        match="pre-deal Manacle disable requires unowned pre-shuffle physical deck order",
    ):
        prepare_supported_resource_boss_start(run)

    assert run.public.hand_size == original_hand_size
    assert run.boss_hand_size_sub is None
    assert not getattr(run.public.blind, "disabled", False)


def test_env_r2_chicot_is_inert_on_nonboss_blind():
    run = _run(boss_name=None, blind_type=BlindType.BIG)
    run.public.jokers = [ChicotJoker()]

    result = prepare_supported_nonboss_blind_start(run)

    assert result.public.phase == "DRAW_TO_HAND"
    assert result.public.hands_remaining == 4
    assert result.public.discards_remaining == 3
    assert not getattr(result.public.blind, "disabled", False)


def test_env_r2_multiple_chicot_boss_disable_requests_fail_closed():
    run = _run(boss_name="The Water")
    run.public.jokers = [ChicotJoker(), ChicotJoker()]

    with pytest.raises(
        HeadlessTransitionError,
        match="multiple queued Chicot Boss disables",
    ):
        prepare_supported_resource_boss_start(run)

    assert not getattr(run.public.blind, "disabled", False)
    assert run.boss_discards_sub is None


def test_env_r2_chicot_disables_amber_after_hidden_order_effect_without_rng_reversal():
    run = _run(boss_name="Amber Acorn")
    run.public.jokers = [ChicotJoker()]
    # Amber requires simulator-retained Joker creation/physical order. Rebuild
    # the run after installing the Joker so private order matches public state.
    run = HeadlessRunState(public=run.public, seed="CHICOT")
    before_rng = run.rng_snapshot()

    result = prepare_supported_amber_acorn_start(run)

    # One Joker is flipped/revealed but Amber consumes no shuffle RNG for a
    # single-card Joker area. Chicot then disables Amber before round-start deal.
    assert result.public.blind.disabled is True
    assert result.rng_snapshot() == before_rng
    assert result.public.jokers[0].__class__ is ChicotJoker


def test_env_r2_chicot_disables_crimson_and_clears_prepped_before_initial_draw():
    run = _run(boss_name="Crimson Heart")
    run.public.jokers = [ChicotJoker()]

    result = prepare_supported_crimson_heart_start(run)

    assert result.public.blind.disabled is True
    assert getattr(result.public.blind, "prepped", False) is False
    assert result.public.jokers[0].debuffed is False
