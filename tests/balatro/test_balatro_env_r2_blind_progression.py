import pytest

from games.balatro.env.blind_progression import (
    BlindProgressionError,
    BlindProgressionState,
    enter_blind_select_progression,
    finalize_won_round_progression,
    reset_blinds_after_boss_cashout,
)
from games.balatro.env.transition import HeadlessRunState
from games.balatro.state import BalatroState


def _won_run(*, ante: int = 3) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "ROUND_EVAL"
    state.ante = ante
    state.score = 1_000
    state.blind_score = 600
    return HeadlessRunState(
        public=state,
        seed="PROGRESSION",
        round_bonus_hands=2,
        round_bonus_discards=3,
    )


def _progression(blind_type: str, *, ante: int = 3) -> BlindProgressionState:
    kwargs = {
        "small_status": "Defeated",
        "big_status": "Defeated",
        "boss_status": "Upcoming",
        "blind_on_deck": blind_type,
        "blind_ante": ante,
        "boss_name": "The Hook",
    }
    kwargs[f"{blind_type.lower()}_status"] = "Current"
    return BlindProgressionState(**kwargs)


@pytest.mark.parametrize("blind_type", ["Small", "Big"])
def test_env_r2_nonboss_end_round_marks_only_current_blind_defeated(blind_type):
    run = _won_run()
    progression = _progression(blind_type)

    result, result_progression = finalize_won_round_progression(
        run,
        progression,
        blind_type=blind_type,
    )

    assert result_progression.status_for(blind_type) == "Defeated"
    assert result.public.ante == 3
    assert result.round_bonus_hands == 2
    assert result.round_bonus_discards == 3
    assert result.public.phase == "ROUND_EVAL"


def test_env_r2_boss_end_round_advances_ante_before_cashout_and_clears_round_bonus():
    run = _won_run(ante=4)
    progression = _progression("Boss", ante=4)

    result, result_progression = finalize_won_round_progression(
        run,
        progression,
        blind_type="Boss",
    )

    assert result_progression.boss_status == "Defeated"
    assert result_progression.blind_on_deck == "Boss"
    assert result_progression.blind_ante == 4
    assert result.public.ante == 5
    assert result.round_bonus_hands == 0
    assert result.round_bonus_discards == 0
    assert result.public.phase == "ROUND_EVAL"


def test_env_r2_end_round_progression_isolates_run_and_private_progression_inputs():
    run = _won_run()
    progression = _progression("Boss")

    result, result_progression = finalize_won_round_progression(
        run,
        progression,
        blind_type="Boss",
    )

    assert result is not run
    assert result_progression is not progression
    assert run.public.ante == 3
    assert run.round_bonus_hands == 2
    assert run.round_bonus_discards == 3
    assert progression.boss_status == "Current"


def test_env_r2_end_round_progression_rejects_loss_or_wrong_phase():
    run = _won_run()
    progression = _progression("Small")

    run.public.score = 599
    with pytest.raises(BlindProgressionError, match="target"):
        finalize_won_round_progression(run, progression, blind_type="Small")

    run = _won_run()
    run.public.phase = "SHOP"
    with pytest.raises(BlindProgressionError, match="ROUND_EVAL"):
        finalize_won_round_progression(run, progression, blind_type="Small")


def test_env_r2_end_round_progression_rejects_mismatched_or_noncurrent_blind():
    run = _won_run()
    progression = _progression("Small")

    with pytest.raises(BlindProgressionError, match="blind_on_deck"):
        finalize_won_round_progression(run, progression, blind_type="Big")

    progression.small_status = "Defeated"
    with pytest.raises(BlindProgressionError, match="current blind status"):
        finalize_won_round_progression(run, progression, blind_type="Small")


def test_env_r2_private_blind_progression_validates_canonical_state():
    with pytest.raises(BlindProgressionError, match="canonical blind-state"):
        BlindProgressionState(small_status="DONE")
    with pytest.raises(BlindProgressionError, match="blind_on_deck"):
        BlindProgressionState(blind_on_deck="Needle")
    with pytest.raises(BlindProgressionError, match="blind_ante"):
        BlindProgressionState(blind_ante=True)
    with pytest.raises(BlindProgressionError, match="at least 1"):
        BlindProgressionState(blind_ante=0)


def test_env_r2_boss_reset_blinds_restores_upcoming_state_for_new_ante():
    progression = BlindProgressionState(
        small_status="Defeated",
        big_status="Skipped",
        boss_status="Defeated",
        blind_on_deck="Boss",
        blind_ante=4,
        boss_name="The Hook",
        boss_rerolled=True,
    )

    result = reset_blinds_after_boss_cashout(
        progression,
        current_ante=5,
        next_boss_name="The Ox",
    )

    assert result.small_status == "Upcoming"
    assert result.big_status == "Upcoming"
    assert result.boss_status == "Upcoming"
    assert result.blind_on_deck == "Small"
    assert result.blind_ante == 5
    assert result.boss_name == "The Ox"
    assert result.boss_rerolled is False


def test_env_r2_boss_reset_blinds_isolates_input_and_requires_source_order_ante():
    progression = BlindProgressionState(
        small_status="Defeated",
        big_status="Defeated",
        boss_status="Defeated",
        blind_on_deck="Boss",
        blind_ante=3,
        boss_name="The Hook",
    )

    result = reset_blinds_after_boss_cashout(
        progression,
        current_ante=4,
        next_boss_name="The Wall",
    )

    assert result is not progression
    assert progression.boss_status == "Defeated"
    assert progression.blind_ante == 3
    assert progression.boss_name == "The Hook"

    with pytest.raises(BlindProgressionError, match="exactly one above"):
        reset_blinds_after_boss_cashout(
            progression,
            current_ante=5,
            next_boss_name="The Wall",
        )


def test_env_r2_boss_reset_blinds_rejects_nonboss_or_nondefeated_boundary():
    wrong_blind = BlindProgressionState(
        small_status="Defeated",
        big_status="Defeated",
        boss_status="Upcoming",
        blind_on_deck="Big",
        blind_ante=3,
        boss_name="The Hook",
    )
    with pytest.raises(BlindProgressionError, match="blind_on_deck"):
        reset_blinds_after_boss_cashout(
            wrong_blind,
            current_ante=4,
            next_boss_name="The Ox",
        )

    not_defeated = BlindProgressionState(
        small_status="Defeated",
        big_status="Defeated",
        boss_status="Current",
        blind_on_deck="Boss",
        blind_ante=3,
        boss_name="The Hook",
    )
    with pytest.raises(BlindProgressionError, match="defeated Boss"):
        reset_blinds_after_boss_cashout(
            not_defeated,
            current_ante=4,
            next_boss_name="The Ox",
        )


def test_env_r2_blind_select_prefers_small_then_big_then_boss_in_source_order():
    fresh = BlindProgressionState(
        small_status="Upcoming",
        big_status="Upcoming",
        boss_status="Upcoming",
        blind_on_deck="Small",
        boss_name="The Hook",
    )
    selected_small = enter_blind_select_progression(fresh)
    assert selected_small.blind_on_deck == "Small"
    assert selected_small.small_status == "Select"

    after_small = BlindProgressionState(
        small_status="Defeated",
        big_status="Upcoming",
        boss_status="Upcoming",
        blind_on_deck="Small",
        boss_name="The Hook",
    )
    selected_big = enter_blind_select_progression(after_small)
    assert selected_big.blind_on_deck == "Big"
    assert selected_big.big_status == "Select"

    after_big = BlindProgressionState(
        small_status="Defeated",
        big_status="Defeated",
        boss_status="Upcoming",
        blind_on_deck="Big",
        boss_name="The Hook",
    )
    selected_boss = enter_blind_select_progression(after_big)
    assert selected_boss.blind_on_deck == "Boss"
    assert selected_boss.boss_status == "Select"


def test_env_r2_blind_select_treats_skipped_and_hidden_nonboss_blinds_as_terminal():
    progression = BlindProgressionState(
        small_status="Skipped",
        big_status="Hide",
        boss_status="Upcoming",
        blind_on_deck="Small",
        boss_name="The Hook",
    )

    result = enter_blind_select_progression(progression)

    assert result.blind_on_deck == "Boss"
    assert result.boss_status == "Select"


def test_env_r2_blind_select_rejects_stale_current_or_unreset_defeated_boss():
    current = BlindProgressionState(
        small_status="Current",
        big_status="Upcoming",
        boss_status="Upcoming",
    )
    with pytest.raises(BlindProgressionError, match="still Current"):
        enter_blind_select_progression(current)

    defeated_boss = BlindProgressionState(
        small_status="Defeated",
        big_status="Defeated",
        boss_status="Defeated",
        blind_on_deck="Boss",
        boss_name="The Hook",
    )
    with pytest.raises(BlindProgressionError, match="reset_blinds"):
        enter_blind_select_progression(defeated_boss)


def test_env_r2_blind_select_isolates_progression_input():
    progression = BlindProgressionState(
        small_status="Defeated",
        big_status="Upcoming",
        boss_status="Upcoming",
        blind_on_deck="Small",
        boss_name="The Hook",
    )

    result = enter_blind_select_progression(progression)

    assert result is not progression
    assert progression.blind_on_deck == "Small"
    assert progression.big_status == "Upcoming"
    assert result.blind_on_deck == "Big"
    assert result.big_status == "Select"
