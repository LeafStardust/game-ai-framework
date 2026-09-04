import pytest

from games.balatro.env.boss_selection import (
    ALL_BOSS_KEYS,
    BossSelectionError,
    BossSelectionState,
    select_normal_boss,
)
from games.balatro.env.transition import HeadlessRunState
from games.balatro.state import BalatroState


def _run(seed: str = "TESTSEED") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    return HeadlessRunState(public=state, seed=seed)


def test_env_r2_boss_selection_initializes_every_vanilla_boss_usage_to_zero():
    selection = BossSelectionState()

    assert len(ALL_BOSS_KEYS) == 28
    assert set(selection.usage_counts) == ALL_BOSS_KEYS
    assert set(selection.usage_counts.values()) == {0}
    assert selection.win_ante == 8


def test_env_r2_boss_selection_pins_ante_two_key_sort_and_boss_rng_vector():
    run = _run()
    selection = BossSelectionState()

    result_run, result_selection, result = select_normal_boss(
        run,
        selection,
        ante=2,
    )

    # Vanilla eligible table has 18 least-used keys at Ante 2. String-key
    # sorting followed by pseudoseed('boss') for TESTSEED picks bl_hook.
    assert result.boss_key == "bl_hook"
    assert result.boss_name == "The Hook"
    assert result_selection.usage_counts["bl_hook"] == 1
    assert sum(result_selection.usage_counts.values()) == 1
    assert result_run.rng.nodes["boss"] == 0.9912295796516


def test_env_r2_boss_selection_least_used_filter_prevents_immediate_repeat():
    run = _run()
    selection = BossSelectionState()

    run, selection, first = select_normal_boss(run, selection, ante=2)
    run, selection, second = select_normal_boss(run, selection, ante=2)

    assert first.boss_key == "bl_hook"
    assert second.boss_key == "bl_wall"
    assert selection.usage_counts["bl_hook"] == 1
    assert selection.usage_counts["bl_wall"] == 1
    assert run.rng.nodes["boss"] == 0.8436428251073


def test_env_r2_boss_selection_ante_eight_uses_only_showdown_pool():
    result_run, selection, result = select_normal_boss(
        _run(),
        BossSelectionState(),
        ante=8,
    )

    assert result.boss_key == "bl_final_bell"
    assert result.boss_name == "Cerulean Bell"
    assert selection.usage_counts["bl_final_bell"] == 1
    assert sum(selection.usage_counts.values()) == 1
    assert result_run.rng.nodes["boss"] == 0.9912295796516


def test_env_r2_boss_selection_respects_source_min_ante_and_banned_keys():
    selection = BossSelectionState(banned_keys=frozenset({"bl_head"}))
    # At Ante 1 only min=1 ordinary Bosses are eligible. Ban one and mark every
    # other Ante-1 candidate used except The Hook so least-use filtering is exact.
    ante_one_keys = {
        "bl_club",
        "bl_goad",
        "bl_head",
        "bl_hook",
        "bl_manacle",
        "bl_pillar",
        "bl_psychic",
        "bl_window",
    }
    for key in ante_one_keys - {"bl_head", "bl_hook"}:
        selection.usage_counts[key] = 1

    _, result_selection, result = select_normal_boss(
        _run(),
        selection,
        ante=1,
    )

    assert result.boss_key == "bl_hook"
    assert result_selection.usage_counts["bl_hook"] == 1
    assert result_selection.usage_counts["bl_head"] == 0


def test_env_r2_boss_selection_isolates_input_usage_and_rng_state():
    run = _run()
    selection = BossSelectionState()
    before_rng = run.rng_snapshot()
    before_usage = dict(selection.usage_counts)

    result_run, result_selection, _ = select_normal_boss(run, selection, ante=2)

    assert run.rng_snapshot() == before_rng
    assert selection.usage_counts == before_usage
    assert result_run.rng_snapshot() != before_rng
    assert result_selection.usage_counts != before_usage


def test_env_r2_boss_selection_fails_closed_on_invalid_private_state():
    with pytest.raises(BossSelectionError, match="every vanilla Boss key"):
        BossSelectionState(usage_counts={"bl_hook": 0})

    invalid = BossSelectionState()
    invalid.usage_counts["bl_hook"] = -1
    with pytest.raises(BossSelectionError, match="nonnegative"):
        BossSelectionState(usage_counts=invalid.usage_counts)

    with pytest.raises(BossSelectionError, match="win_ante"):
        BossSelectionState(win_ante=True)

    with pytest.raises(BossSelectionError, match="ante"):
        select_normal_boss(_run(), BossSelectionState(), ante=0)


def test_env_r2_boss_selection_fails_closed_when_all_eligible_bosses_are_banned():
    selection = BossSelectionState(
        banned_keys=frozenset(
            {
                "bl_club",
                "bl_goad",
                "bl_head",
                "bl_hook",
                "bl_manacle",
                "bl_pillar",
                "bl_psychic",
                "bl_window",
            }
        )
    )

    with pytest.raises(BossSelectionError, match="no eligible"):
        select_normal_boss(_run(), selection, ante=1)
