import pytest

from games.balatro.env.blind_progression import (
    BlindProgressionError,
    BlindProgressionState,
    finalize_won_round_progression,
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
