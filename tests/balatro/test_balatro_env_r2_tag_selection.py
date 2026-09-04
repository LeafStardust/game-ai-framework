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

    # The chosen slot is the same in this pinned vector because vanilla keeps
    # unavailable entries in-place instead of compressing the dense 24-slot pool.
    assert locked_tag == discovered_tag == "tag_buffoon"
    assert locked_run.rng_snapshot() == discovered_run.rng_snapshot()


def test_env_r2_tag_selection_resamples_unavailable_slot_with_source_key_suffixes():
    result_run, tag = select_normal_tag(
        _run("S0"),
        TagProfileState(frozenset()),
        ante=1,
    )

    # S0 first indexes min-Ante-2 tag_standard, then another unavailable slot;
    # vanilla retries against the same pool with _resample2/_resample3.
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

    with pytest.raises(TagSelectionError, match="ante"):
        select_normal_tag(
            _run(),
            TagProfileState(frozenset()),
            ante=0,
        )

    with pytest.raises(TagSelectionError, match="append"):
        select_normal_tag(
            _run(),
            TagProfileState(frozenset()),
            ante=2,
            append=1,  # type: ignore[arg-type]
        )
