import pytest

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.env.crimson_heart import (
    apply_crimson_heart_drawn_to_hand,
    arm_crimson_heart_after_play,
    clear_crimson_heart_joker_debuffs,
    set_crimson_heart_prepped,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.state import BalatroState


def _run(*, joker_count: int = 3) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SELECTING_HAND"
    state.boss_name = "Crimson Heart"
    state.blind = Blind(BlindType.BOSS, 1000)
    state.jokers = []
    for index in range(joker_count):
        joker = FlatMultJoker(index + 1)
        joker.live_id = 100 + index
        joker.debuffed = False
        state.jokers.append(joker)
    state.hand = [BalatroCard("A", "Spades"), BalatroCard("K", "Hearts")]
    return HeadlessRunState(public=state, seed="CRIMSON")


def _debuffed_ids(run: HeadlessRunState) -> list[int]:
    return [
        joker.live_id
        for joker in run.public.jokers
        if bool(getattr(joker, "debuffed", False))
    ]


def test_env_r2_crimson_draw_requires_prepped_and_consumes_no_rng_otherwise():
    run = _run()
    before = run.rng_snapshot()

    result = apply_crimson_heart_drawn_to_hand(run)

    assert _debuffed_ids(result) == []
    assert result.rng_snapshot() == before
    assert _debuffed_ids(run) == []


def test_env_r2_crimson_initial_draw_selects_exactly_one_joker_and_isolates_input():
    run = set_crimson_heart_prepped(_run(), True)
    before_rng = run.rng_snapshot()

    result = apply_crimson_heart_drawn_to_hand(run)

    assert len(_debuffed_ids(result)) == 1
    assert _debuffed_ids(run) == []
    assert result.rng_snapshot() != before_rng
    assert getattr(result.public.blind, "prepped") is False
    assert getattr(run.public.blind, "prepped") is True


def test_env_r2_crimson_multi_joker_reselection_excludes_previous_target():
    run = set_crimson_heart_prepped(_run(joker_count=3), True)
    first = apply_crimson_heart_drawn_to_hand(run)
    previous = _debuffed_ids(first)
    assert len(previous) == 1

    first = set_crimson_heart_prepped(first, True)
    second = apply_crimson_heart_drawn_to_hand(first)

    assert len(_debuffed_ids(second)) == 1
    assert _debuffed_ids(second) != previous


def test_env_r2_crimson_single_joker_can_be_reselected():
    run = set_crimson_heart_prepped(_run(joker_count=1), True)
    first = apply_crimson_heart_drawn_to_hand(run)
    assert _debuffed_ids(first) == [100]

    first = set_crimson_heart_prepped(first, True)
    second = apply_crimson_heart_drawn_to_hand(first)

    assert _debuffed_ids(second) == [100]


def test_env_r2_crimson_empty_joker_area_clears_prepped_without_rng():
    run = set_crimson_heart_prepped(_run(joker_count=0), True)
    before = run.rng_snapshot()

    result = apply_crimson_heart_drawn_to_hand(run)

    assert result.public.jokers == []
    assert getattr(result.public.blind, "prepped") is False
    assert result.rng_snapshot() == before


def test_env_r2_crimson_press_play_arms_next_draw_only_when_joker_exists():
    run = _run(joker_count=2)
    action = BalatroAction(PLAY_CARDS, cards=[run.public.hand[0]])

    armed = arm_crimson_heart_after_play(run, action)

    assert getattr(armed.public.blind, "prepped") is True
    assert not hasattr(run.public.blind, "prepped")

    empty = _run(joker_count=0)
    empty_action = BalatroAction(PLAY_CARDS, cards=[empty.public.hand[0]])
    unarmed = arm_crimson_heart_after_play(empty, empty_action)
    assert not hasattr(unarmed.public.blind, "prepped")


def test_env_r2_crimson_press_play_rejects_non_hand_card():
    run = _run()
    outsider = BalatroCard("2", "Clubs")

    with pytest.raises(HeadlessTransitionError, match="current-hand"):
        arm_crimson_heart_after_play(
            run,
            BalatroAction(PLAY_CARDS, cards=[outsider]),
        )


def test_env_r2_crimson_cleanup_clears_target_and_prepped():
    run = set_crimson_heart_prepped(_run(), True)
    targeted = apply_crimson_heart_drawn_to_hand(run)
    assert len(_debuffed_ids(targeted)) == 1
    setattr(targeted.public.blind, "prepped", True)

    cleaned = clear_crimson_heart_joker_debuffs(targeted)

    assert _debuffed_ids(cleaned) == []
    assert getattr(cleaned.public.blind, "prepped") is False


def test_env_r2_crimson_requires_exact_joker_creation_order_for_multiple_jokers():
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SELECTING_HAND"
    state.boss_name = "Crimson Heart"
    state.blind = Blind(BlindType.BOSS, 1000)
    state.jokers = [FlatMultJoker(1), FlatMultJoker(2)]
    run = HeadlessRunState(public=state, seed="CRIMSON")
    assert run.joker_order_state is None
    setattr(run.public.blind, "prepped", True)

    with pytest.raises(HeadlessTransitionError, match="creation order"):
        apply_crimson_heart_drawn_to_hand(run)
