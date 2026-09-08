from games.balatro.env.blind_progression import BlindProgressionState
from games.balatro.env.boss_cashout_generation import generate_post_boss_cashout_choices
from games.balatro.env.boss_selection import ALL_BOSS_KEYS, BossSelectionState
from games.balatro.env.tag_selection import ALL_TAG_KEYS, TagProfileState
from games.balatro.env.transition import HeadlessRunState
from games.balatro.state import BalatroState


def _run(seed: str = "PREANTE-CASHOUT") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.ante = 0
    return HeadlessRunState(public=state, seed=seed)


def _progression() -> BlindProgressionState:
    return BlindProgressionState(
        small_status="Defeated",
        big_status="Defeated",
        boss_status="Defeated",
        blind_on_deck="Boss",
        blind_ante=-1,
        boss_name="The Hook",
        boss_rerolled=True,
    )


def _selection() -> BossSelectionState:
    selection = BossSelectionState()
    selection.usage_counts["bl_hook"] = 1
    return selection


def test_env_r2_preante_post_boss_generation_composes_literal_ante_zero():
    result = generate_post_boss_cashout_choices(
        _run(),
        _progression(),
        _selection(),
        TagProfileState(frozenset()),
    )

    assert result.small_tag in ALL_TAG_KEYS
    assert result.big_tag in ALL_TAG_KEYS
    assert result.boss.boss_key in ALL_BOSS_KEYS
    assert result.progression.small_status == "Upcoming"
    assert result.progression.big_status == "Upcoming"
    assert result.progression.boss_status == "Upcoming"
    assert result.progression.blind_on_deck == "Small"
    assert result.progression.blind_ante == 0
    assert result.progression.boss_name == result.boss.boss_name
    assert result.progression.boss_rerolled is False
    assert "Tag0" in result.run.rng.nodes
    assert "boss" in result.run.rng.nodes


def test_env_r2_preante_post_boss_generation_is_replay_deterministic():
    first = generate_post_boss_cashout_choices(
        _run(),
        _progression(),
        _selection(),
        TagProfileState(frozenset()),
    )
    second = generate_post_boss_cashout_choices(
        _run(),
        _progression(),
        _selection(),
        TagProfileState(frozenset()),
    )

    assert first.small_tag == second.small_tag
    assert first.big_tag == second.big_tag
    assert first.boss == second.boss
    assert first.run.rng_snapshot() == second.run.rng_snapshot()
