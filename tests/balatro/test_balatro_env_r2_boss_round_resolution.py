import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_progression import BlindProgressionError, BlindProgressionState
from games.balatro.env.boss_round_resolution import resolve_supported_boss_round
from games.balatro.env.boss_selection import BossSelectionState
from games.balatro.env.deal import deal_supported_round_start
from games.balatro.env.tag_selection import TagProfileState
from games.balatro.env.transition import HeadlessRunState
from games.balatro.state import BalatroState


def _cleared_hook_run() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "DRAW_TO_HAND"
    state.ante = 1
    state.money = 14
    state.hand_size = 8
    state.boss_name = "The Hook"
    state.blind_is_boss = True
    state.blind = Blind(BlindType.BOSS, requirement=100, reward=5)
    state.blind_score = 100

    run = HeadlessRunState(public=state, seed="TESTSEED")
    dealt = deal_supported_round_start(run)
    dealt.public.phase = "ROUND_EVAL"
    dealt.public.score = 120
    dealt.public.hands_remaining = 1
    return dealt


def _progression() -> BlindProgressionState:
    return BlindProgressionState(
        small_status="Defeated",
        big_status="Defeated",
        boss_status="Current",
        blind_on_deck="Boss",
        blind_ante=1,
        boss_name="The Hook",
    )


def _selection() -> BossSelectionState:
    result = BossSelectionState()
    result.usage_counts["bl_hook"] = 1
    return result


def test_env_r2_composed_boss_round_pins_cashout_ante_and_next_choices():
    result = resolve_supported_boss_round(
        _cleared_hook_run(),
        _progression(),
        _selection(),
        TagProfileState(frozenset()),
    )

    # end_round advances the Ante before the supported Boss cash-out; the cash-out
    # then pays $5 Boss reward + $1 unused hand + $2 pre-payout interest.
    assert result.run.public.ante == 2
    assert result.run.public.money == 22
    assert result.run.public.phase == "SHOP"
    assert result.run.public.shop_active is True
    assert result.run.public.shop_jokers == []
    assert result.run.public.shop_consumables == []
    assert result.run.public.shop_boosters == []
    assert result.run.public.shop_vouchers == []

    # Next-Ante generation consumes Small Tag -> Big Tag -> Boss in source order.
    assert result.small_tag == "tag_buffoon"
    assert result.big_tag == "tag_meteor"
    assert result.next_boss_key == "bl_house"
    assert result.next_boss_name == "The House"
    assert result.run.rng.nodes["Tag2"] == 0.7956689640881
    assert result.run.rng.nodes["boss"] == 0.9912295796516

    assert result.progression.small_status == "Upcoming"
    assert result.progression.big_status == "Upcoming"
    assert result.progression.boss_status == "Upcoming"
    assert result.progression.blind_on_deck == "Small"
    assert result.progression.blind_ante == 2
    assert result.progression.boss_name == "The House"
    assert result.boss_selection.usage_counts["bl_hook"] == 1
    assert result.boss_selection.usage_counts["bl_house"] == 1


def test_env_r2_composed_boss_round_isolates_all_inputs_and_advances_only_output_rng():
    run = _cleared_hook_run()
    progression = _progression()
    selection = _selection()
    tag_profile = TagProfileState(frozenset())
    before_rng = run.rng_snapshot()
    before_money = run.public.money
    before_ante = run.public.ante
    before_usage = dict(selection.usage_counts)

    result = resolve_supported_boss_round(run, progression, selection, tag_profile)

    assert run.public.phase == "ROUND_EVAL"
    assert run.public.money == before_money
    assert run.public.ante == before_ante
    assert run.rng_snapshot() == before_rng
    assert progression.boss_status == "Current"
    assert progression.blind_ante == 1
    assert progression.boss_name == "The Hook"
    assert selection.usage_counts == before_usage
    assert result.run.rng_snapshot() != before_rng


def test_env_r2_composed_boss_round_propagates_progression_precondition_failures():
    run = _cleared_hook_run()
    run.public.score = 99

    with pytest.raises(BlindProgressionError, match="target"):
        resolve_supported_boss_round(
            run,
            _progression(),
            _selection(),
            TagProfileState(frozenset()),
        )
