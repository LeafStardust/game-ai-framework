import pytest

from games.balatro.env.blind_progression import (
    BlindProgressionError,
    BlindProgressionState,
    finalize_won_round_progression,
)
from games.balatro.env.boss_cashout_generation import generate_post_boss_cashout_choices
from games.balatro.env.boss_selection import BOSS_KEY_BY_NAME, BossSelectionState
from games.balatro.env.tag_selection import TagProfileState
from games.balatro.env.transition import HeadlessRunState
from games.balatro.state import BalatroState


def _won_boss_run() -> tuple[HeadlessRunState, BlindProgressionState]:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "ROUND_EVAL"
    state.ante = 2
    state.score = 1_000
    state.blind_score = 600
    progression = BlindProgressionState(
        small_status="Defeated",
        big_status="Defeated",
        boss_status="Current",
        blind_on_deck="Boss",
        blind_ante=2,
        boss_name="The Hook",
    )
    return (
        HeadlessRunState(
            public=state,
            seed="RETAINED-PROGRESSION",
            blind_progression_state=progression,
        ),
        progression,
    )


def test_env_r2_won_round_updates_retained_progression_atomically():
    run, progression = _won_boss_run()

    result, returned = finalize_won_round_progression(
        run, progression, blind_type="Boss"
    )

    assert result.public.ante == 3
    assert returned.boss_status == "Defeated"
    assert result.require_blind_progression_state() == returned
    assert result.require_blind_progression_state() is not returned
    assert run.require_blind_progression_state().boss_status == "Current"


def test_env_r2_won_round_rejects_conflicting_parallel_progression():
    run, progression = _won_boss_run()
    conflicting = BlindProgressionState(
        small_status="Defeated",
        big_status="Defeated",
        boss_status="Current",
        blind_on_deck="Boss",
        blind_ante=1,
        boss_name="The Hook",
    )

    with pytest.raises(BlindProgressionError, match="conflicts with retained"):
        finalize_won_round_progression(run, conflicting, blind_type="Boss")

    assert run.require_blind_progression_state() == progression
    assert run.public.ante == 2


def _boss_cashout_run() -> tuple[HeadlessRunState, BlindProgressionState, BossSelectionState]:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.ante = 3
    progression = BlindProgressionState(
        small_status="Defeated",
        big_status="Defeated",
        boss_status="Defeated",
        blind_on_deck="Boss",
        blind_ante=2,
        boss_name="The Hook",
        boss_rerolled=True,
    )
    selection = BossSelectionState()
    selection.usage_counts[BOSS_KEY_BY_NAME["The Hook"]] = 1
    run = HeadlessRunState(
        public=state,
        seed="RETAINED-CASHOUT",
        blind_progression_state=progression,
    )
    return run, progression, selection


def test_env_r2_post_boss_generation_replaces_retained_progression():
    run, progression, selection = _boss_cashout_run()

    result = generate_post_boss_cashout_choices(
        run,
        progression,
        selection,
        TagProfileState(frozenset()),
    )

    retained = result.run.require_blind_progression_state()
    assert retained == result.progression
    assert retained is not result.progression
    assert retained.blind_ante == 3
    assert retained.blind_on_deck == "Small"
    assert retained.boss_status == "Upcoming"
    assert retained.boss_name == result.boss.boss_name
    assert progression.blind_ante == 2
    assert progression.boss_status == "Defeated"


def test_env_r2_post_boss_generation_rejects_conflicting_retained_progression_before_rng():
    run, progression, selection = _boss_cashout_run()
    before_rng = run.rng_snapshot()
    conflicting = BlindProgressionState(
        small_status="Defeated",
        big_status="Defeated",
        boss_status="Defeated",
        blind_on_deck="Boss",
        blind_ante=1,
        boss_name="The Hook",
    )

    with pytest.raises(BlindProgressionError, match="conflicts with retained"):
        generate_post_boss_cashout_choices(
            run,
            conflicting,
            selection,
            TagProfileState(frozenset()),
        )

    assert run.rng_snapshot() == before_rng
    assert run.require_blind_progression_state() == progression
