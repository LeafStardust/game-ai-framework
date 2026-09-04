import pytest

from games.balatro.env.blind_progression import (
    BlindProgressionError,
    BlindProgressionState,
)
from games.balatro.env.boss_cashout_generation import (
    generate_post_boss_cashout_choices,
)
from games.balatro.env.boss_selection import BossSelectionError, BossSelectionState
from games.balatro.env.tag_selection import TagProfileState
from games.balatro.env.transition import HeadlessRunState
from games.balatro.state import BalatroState


def _run(seed: str = "TESTSEED", *, ante: int = 2) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.ante = ante
    return HeadlessRunState(public=state, seed=seed)


def _progression(*, blind_ante: int = 1, boss_name: str = "The Hook") -> BlindProgressionState:
    return BlindProgressionState(
        small_status="Defeated",
        big_status="Defeated",
        boss_status="Defeated",
        blind_on_deck="Boss",
        blind_ante=blind_ante,
        boss_name=boss_name,
        boss_rerolled=True,
    )


def _selection(*, current_boss_key: str = "bl_hook") -> BossSelectionState:
    result = BossSelectionState()
    result.usage_counts[current_boss_key] = 1
    return result


def test_env_r2_post_boss_generation_pins_tag_tag_boss_source_order():
    result = generate_post_boss_cashout_choices(
        _run(),
        _progression(),
        _selection(),
        TagProfileState(frozenset()),
    )

    assert result.small_tag == "tag_buffoon"
    assert result.big_tag == "tag_meteor"
    # The just-defeated Hook has use count 1, so least-used filtering removes it
    # from the Ante-2 Boss pool before the TESTSEED boss draw.
    assert result.boss.boss_key == "bl_house"
    assert result.boss.boss_name == "The House"
    assert result.run.rng.nodes["Tag2"] == 0.7956689640881
    assert result.run.rng.nodes["boss"] == 0.9912295796516


def test_env_r2_post_boss_generation_applies_reset_blinds_after_choices():
    result = generate_post_boss_cashout_choices(
        _run(),
        _progression(),
        _selection(),
        TagProfileState(frozenset()),
    )

    progression = result.progression
    assert progression.small_status == "Upcoming"
    assert progression.big_status == "Upcoming"
    assert progression.boss_status == "Upcoming"
    assert progression.blind_on_deck == "Small"
    assert progression.blind_ante == 2
    assert progression.boss_name == "The House"
    assert progression.boss_rerolled is False
    assert result.boss_selection.usage_counts["bl_hook"] == 1
    assert result.boss_selection.usage_counts["bl_house"] == 1
    assert sum(result.boss_selection.usage_counts.values()) == 2


def test_env_r2_post_boss_generation_profile_state_controls_tag_pool_without_affecting_boss_pool():
    result = generate_post_boss_cashout_choices(
        _run(),
        _progression(),
        _selection(),
        TagProfileState(
            frozenset(
                {"j_blueprint", "e_negative", "e_foil", "e_holo", "e_polychrome"}
            )
        ),
    )

    assert result.small_tag == "tag_buffoon"
    assert result.big_tag == "tag_meteor"
    assert result.boss.boss_key == "bl_house"


def test_env_r2_post_boss_generation_isolates_all_inputs():
    run = _run()
    progression = _progression()
    selection = _selection()
    before_rng = run.rng_snapshot()
    before_usage = dict(selection.usage_counts)

    result = generate_post_boss_cashout_choices(
        run,
        progression,
        selection,
        TagProfileState(frozenset()),
    )

    assert run.rng_snapshot() == before_rng
    assert progression.boss_status == "Defeated"
    assert progression.blind_ante == 1
    assert progression.boss_name == "The Hook"
    assert selection.usage_counts == before_usage
    assert result.run.rng_snapshot() != before_rng


def test_env_r2_post_boss_generation_requires_exact_cashout_boundary():
    run = _run()
    run.public.phase = "BLIND_SELECT"
    with pytest.raises(BlindProgressionError, match="active SHOP"):
        generate_post_boss_cashout_choices(
            run,
            _progression(),
            _selection(),
            TagProfileState(frozenset()),
        )

    run = _run()
    run.public.shop_jokers.append(object())
    with pytest.raises(BlindProgressionError, match="ungenerated"):
        generate_post_boss_cashout_choices(
            run,
            _progression(),
            _selection(),
            TagProfileState(frozenset()),
        )


def test_env_r2_post_boss_generation_requires_end_round_ante_advance_and_defeated_boss():
    with pytest.raises(BlindProgressionError, match="Ante advancement"):
        generate_post_boss_cashout_choices(
            _run(ante=3),
            _progression(blind_ante=1),
            _selection(),
            TagProfileState(frozenset()),
        )

    progression = _progression()
    progression.boss_status = "Current"
    with pytest.raises(BlindProgressionError, match="defeated Boss progression"):
        generate_post_boss_cashout_choices(
            _run(),
            progression,
            _selection(),
            TagProfileState(frozenset()),
        )


def test_env_r2_post_boss_generation_requires_consistent_current_boss_usage_state():
    selection = BossSelectionState()

    with pytest.raises(BossSelectionError, match="does not record"):
        generate_post_boss_cashout_choices(
            _run(),
            _progression(),
            selection,
            TagProfileState(frozenset()),
        )

    with pytest.raises(BossSelectionError, match="vanilla Boss identity"):
        generate_post_boss_cashout_choices(
            _run(),
            _progression(boss_name="Not A Boss"),
            BossSelectionState(),
            TagProfileState(frozenset()),
        )
