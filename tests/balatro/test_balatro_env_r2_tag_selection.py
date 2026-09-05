import pytest

from games.balatro.env.tag_selection import (
    ALL_TAG_KEYS,
    TAG_REQUIREMENT_KEYS,
    TagProfileState,
    TagSelectionError,
    select_normal_tag,
)
from games.balatro.env.transition import HeadlessRunState
from games.balatro.state import BalatroState


def _run(seed: str = "TESTSEED") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    return HeadlessRunState(public=state, seed=seed)


def test_env_r2_tag_selection_pins_vanilla_tag_roster_and_profile_requirements():
    assert len(ALL_TAG_KEYS) == 24
    assert TAG_REQUIREMENT_KEYS == {
        "j_blueprint",
        "e_negative",
        "e_foil",
        "e_holo",
        "e_polychrome",
    }


def test_env_r2_tag_selection_pins_testseed_ante_two_vector_without_unlock_assumptions():
    result_run, tag = select_normal_tag(
        _run(),
        TagProfileState(frozenset()),
        ante=2,
    )

    assert tag == "tag_buffoon"
    assert result_run.rng.nodes["Tag2"] == 0.3834662199002


def test_env_r2_tag_selection_two_consecutive_choices_advance_same_keyed_queue():
    run = _run()
    profile = TagProfileState(frozenset())

    run, small_tag = select_normal_tag(run, profile, ante=2)
    run, big_tag = select_normal_tag(run, profile, ante=2)

    assert small_tag == "tag_buffoon"
    assert big_tag == "tag_meteor"
    assert run.rng.nodes["Tag2"] == 0.7956689640881


def test_env_r2_tag_selection_profile_discovery_does_not_compress_pool_slots():
    locked_profile = TagProfileState(frozenset())
    discovered_profile = TagProfileState(TAG_REQUIREMENT_KEYS)

    locked_run, locked_tag = select_normal_tag(_run(), locked_profile, ante=2)
    discovered_run, discovered_tag = select_normal_tag(
        _run(),
        discovered_profile,
        ante=2,
    )

    assert locked_tag == discovered_tag == "tag_buffoon"
    assert locked_run.rng_snapshot() == discovered_run.rng_snapshot()


def test_env_r2_tag_selection_resamples_unavailable_slot_with_source_key_suffixes():
    result_run, tag = select_normal_tag(
        _run("S0"),
        TagProfileState(frozenset()),
        ante=1,
    )

    assert tag == "tag_uncommon"
    assert result_run.rng.nodes["Tag1"] == 0.8718027350855
    assert result_run.rng.nodes["Tag1_resample2"] == 0.3647417563928
    assert result_run.rng.nodes["Tag1_resample3"] == 0.5361623037718


def test_env_r2_tag_selection_ante_one_excludes_min_ante_two_slots_without_removing_them():
    result_run, tag = select_normal_tag(
        _run(),
        TagProfileState(frozenset()),
        ante=1,
    )

    assert tag == "tag_economy"
    assert result_run.rng.nodes["Tag1"] == 0.683310700163


def test_env_r2_tag_selection_preante_uses_literal_ante_for_pool_and_rng_key():
    min_ante_two_tags = {
        "tag_negative",
        "tag_standard",
        "tag_meteor",
        "tag_buffoon",
        "tag_handy",
        "tag_garbage",
        "tag_ethereal",
        "tag_top_up",
        "tag_orbital",
    }
    profile = TagProfileState(frozenset())

    for ante in (0, -1):
        result_run, tag = select_normal_tag(_run(), profile, ante=ante)
        assert tag in ALL_TAG_KEYS
        assert tag not in min_ante_two_tags
        assert f"Tag{ante}" in result_run.rng.nodes


def test_env_r2_tag_selection_isolates_input_rng():
    run = _run()
    before = run.rng_snapshot()

    result_run, _ = select_normal_tag(
        run,
        TagProfileState(frozenset()),
        ante=2,
    )

    assert run.rng_snapshot() == before
    assert result_run.rng_snapshot() != before


def test_env_r2_tag_selection_validates_profile_and_parameters_fail_closed():
    with pytest.raises(TagSelectionError, match="frozenset"):
        TagProfileState(set())  # type: ignore[arg-type]

    with pytest.raises(TagSelectionError, match="only strings"):
        TagProfileState(frozenset({1}))  # type: ignore[arg-type]

    for invalid_ante in (True, 0.5, "0"):
        with pytest.raises(TagSelectionError, match="exact integer"):
            select_normal_tag(
                _run(),
                TagProfileState(frozenset()),
                ante=invalid_ante,  # type: ignore[arg-type]
            )

    with pytest.raises(TagSelectionError, match="append"):
        select_normal_tag(
            _run(),
            TagProfileState(frozenset()),
            ante=2,
            append=1,  # type: ignore[arg-type]
        )
