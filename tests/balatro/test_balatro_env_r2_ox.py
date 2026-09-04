import pytest

from games.balatro.env.boss_hand import apply_ox_debuff_hand_economy
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run(*, money: int = 12, target: str | None = "PAIR") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SELECTING_HAND"
    state.boss_name = "The Ox"
    state.money = money
    state.round_most_played_hand = target
    return HeadlessRunState(public=state, seed="TESTSEED")


def test_env_r2_ox_matching_hand_sets_money_exactly_to_zero():
    run = _run(money=12)

    result = apply_ox_debuff_hand_economy(run, "PAIR")

    assert result.public.money == 0
    assert run.public.money == 12


def test_env_r2_ox_matching_hand_sets_negative_money_to_zero_too():
    result = apply_ox_debuff_hand_economy(_run(money=-4), "PAIR")

    assert result.public.money == 0


def test_env_r2_ox_nonmatching_hand_leaves_money_unchanged():
    result = apply_ox_debuff_hand_economy(_run(money=17), "FLUSH")

    assert result.public.money == 17


def test_env_r2_ox_uses_frozen_round_target_not_mutable_aggregate_counts():
    run = _run(money=20, target="PAIR")
    run.public.hand_play_counts["FLUSH"] = 999
    run.public.hand_play_counts["PAIR"] = 1

    result = apply_ox_debuff_hand_economy(run, "FLUSH")

    assert result.public.money == 20


def test_env_r2_ox_missing_or_invalid_target_fails_closed():
    with pytest.raises(HeadlessTransitionError, match="authoritative current-round"):
        apply_ox_debuff_hand_economy(_run(target=None), "PAIR")

    with pytest.raises(HeadlessTransitionError, match="authoritative current-round"):
        apply_ox_debuff_hand_economy(_run(target="NOT_A_HAND"), "PAIR")


def test_env_r2_ox_requires_canonical_hand_phase_and_identity():
    run = _run()
    with pytest.raises(HeadlessTransitionError, match="canonical classified"):
        apply_ox_debuff_hand_economy(run, "Pair")

    run = _run()
    run.public.phase = "SHOP"
    with pytest.raises(HeadlessTransitionError, match="SELECTING_HAND"):
        apply_ox_debuff_hand_economy(run, "PAIR")

    run = _run()
    run.public.boss_name = "The Tooth"
    with pytest.raises(HeadlessTransitionError, match="requires The Ox"):
        apply_ox_debuff_hand_economy(run, "PAIR")
