import pytest

from games.balatro.env.round_lifecycle import (
    apply_round_resource_baseline,
    apply_supported_setting_blind_effects,
    consume_round_bonuses,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.burglar import BurglarJoker
from games.balatro.jokers.juggler import JugglerJoker
from games.balatro.state import BalatroState


def _run(*, hands=4, discards=3, bonus_hands=0, bonus_discards=0):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.round_reset_hands_observed = True
    state.round_reset_hands = hands
    state.round_reset_discards_observed = True
    state.round_reset_discards = discards
    state.hands_remaining = 99
    state.discards_remaining = 99
    state.discards_used = 7
    state.score = 1234
    state.last_played_hand = "PAIR"
    state.round_hand_play_counts["PAIR"] = 2
    return HeadlessRunState(
        public=state,
        seed="ROUND",
        round_bonus_hands=bonus_hands,
        round_bonus_discards=bonus_discards,
    )


def test_env_r2_round_resource_baseline_matches_vanilla_minimum_semantics():
    run = _run(hands=4, discards=3, bonus_hands=-10, bonus_discards=-10)

    result = apply_round_resource_baseline(run)

    assert result.public.hands_remaining == 1
    assert result.public.discards_remaining == 0
    assert result.public.discards_used == 0
    assert result.public.score == 0
    assert result.public.last_played_hand is None
    assert all(value == 0 for value in result.public.round_hand_play_counts.values())
    assert result.round_bonus_hands == -10
    assert result.round_bonus_discards == -10
    assert run.public.hands_remaining == 99
    assert run.public.discards_remaining == 99


def test_env_r2_round_resource_baseline_adds_positive_bonuses_without_consuming_them():
    result = apply_round_resource_baseline(
        _run(hands=4, discards=3, bonus_hands=2, bonus_discards=4)
    )

    assert result.public.hands_remaining == 6
    assert result.public.discards_remaining == 7
    assert result.round_bonus_hands == 2
    assert result.round_bonus_discards == 4


def test_env_r2_burglar_applies_after_resource_baseline_and_preserves_pending_bonus():
    run = _run(hands=4, discards=3, bonus_hands=2, bonus_discards=1)
    run.public.jokers = [BurglarJoker()]
    baseline = apply_round_resource_baseline(run)

    result = apply_supported_setting_blind_effects(baseline)

    assert baseline.public.hands_remaining == 6
    assert baseline.public.discards_remaining == 4
    assert result.public.hands_remaining == 9
    assert result.public.discards_remaining == 0
    assert result.round_bonus_hands == 2
    assert result.round_bonus_discards == 1


def test_env_r2_multiple_burglars_stack_hands_and_zero_discards():
    run = _run()
    run.public.jokers = [BurglarJoker(), BurglarJoker()]
    baseline = apply_round_resource_baseline(run)

    result = apply_supported_setting_blind_effects(baseline)

    assert result.public.hands_remaining == 10
    assert result.public.discards_remaining == 0


def test_env_r2_blind_start_joker_dispatch_fails_closed_on_unclassified_identity():
    run = _run()
    run.public.jokers = [JugglerJoker()]
    baseline = apply_round_resource_baseline(run)

    with pytest.raises(HeadlessTransitionError, match="unsupported identity"):
        apply_supported_setting_blind_effects(baseline)


def test_env_r2_round_bonus_consumption_is_explicit_and_isolated():
    run = _run(bonus_hands=2, bonus_discards=-1)

    result = consume_round_bonuses(run)

    assert result.round_bonus_hands == 0
    assert result.round_bonus_discards == 0
    assert run.round_bonus_hands == 2
    assert run.round_bonus_discards == -1


def test_env_r2_round_resource_baseline_fails_closed_without_observed_resets():
    run = _run()
    run.public.round_reset_hands_observed = False
    with pytest.raises(HeadlessTransitionError, match="authoritative reset allowances"):
        apply_round_resource_baseline(run)

    run = _run()
    run.public.round_reset_discards_observed = False
    with pytest.raises(HeadlessTransitionError, match="authoritative reset allowances"):
        apply_round_resource_baseline(run)
