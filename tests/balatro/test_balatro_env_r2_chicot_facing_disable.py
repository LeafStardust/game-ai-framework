import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.boss_disable import disable_supported_boss
from games.balatro.env.boss_facing import (
    draw_fish_post_play_cards,
    start_supported_deterministic_facing_boss,
    start_supported_fish,
    start_supported_wheel,
)
from games.balatro.env.transition import HeadlessRunState
from games.balatro.jokers.chicot import ChicotJoker
from games.balatro.state import BalatroState


def _run(boss_name: str, *, chicot: bool = True) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 5
    state.round = 12
    state.blind = Blind(BlindType.BOSS, 30000)
    state.boss_name = boss_name
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    if chicot:
        state.jokers = [ChicotJoker()]
    return HeadlessRunState(public=state, seed=f"CHICOT-{boss_name}")


@pytest.mark.parametrize("boss_name", ["The House", "The Mark"])
def test_env_r2_chicot_disabled_deterministic_facing_boss_deals_face_up(boss_name: str):
    result = start_supported_deterministic_facing_boss(_run(boss_name))

    assert result.public.blind.disabled is True
    assert result.public.phase == "SELECTING_HAND"
    assert result.public.hand
    assert all(card.facing_observed for card in result.public.hand)
    assert not any(card.face_down for card in result.public.hand)


def test_env_r2_chicot_disabled_wheel_skips_wheel_rng_and_deals_face_up():
    result = start_supported_wheel(_run("The Wheel"))

    assert result.public.blind.disabled is True
    assert result.public.phase == "SELECTING_HAND"
    assert not any(card.face_down for card in result.public.hand)
    assert all(card.facing_observed for card in result.public.hand)
    assert "wheel" not in result.rng.nodes
    assert f"nr{result.public.ante}" in result.rng.nodes


def test_env_r2_chicot_disabled_fish_post_play_replenishment_stays_face_up():
    result = start_supported_fish(_run("The Fish"))
    assert result.public.blind.disabled is True

    # Model two cards having left the hand after an owned play boundary so the
    # ordinary replenishment owner has exactly two free slots to refill.
    removed = [result.public.hand.pop(), result.public.hand.pop()]
    result.played_pile.extend(removed)
    hand_name = next(iter(result.public.round_hand_play_counts))
    result.public.round_hand_play_counts[hand_name] = 1

    replenished = draw_fish_post_play_cards(result)

    assert len(replenished.public.hand) == replenished.public.hand_size
    assert all(card.facing_observed for card in replenished.public.hand)
    assert not any(card.face_down for card in replenished.public.hand)


@pytest.mark.parametrize("boss_name", ["The House", "The Wheel", "The Mark", "The Fish"])
def test_env_r2_direct_facing_boss_disable_flips_current_hand_face_up(boss_name: str):
    run = _run(boss_name, chicot=False)
    run.public.phase = "SELECTING_HAND"
    run.public.blind_score = run.public.blind.requirement
    run.public.hand = list(run.public.deck[:2])
    for card in run.public.hand:
        card.face_down = True
        card.facing_observed = True

    disabled = disable_supported_boss(run)

    assert disabled.public.blind.disabled is True
    assert all(card.facing_observed for card in disabled.public.hand)
    assert not any(card.face_down for card in disabled.public.hand)
    assert all(card.face_down for card in run.public.hand)
