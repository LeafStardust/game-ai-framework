import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.select_blind import select_blind_exact
from games.balatro.env.serialization import serialize_headless_run_state
from games.balatro.env.tactical_transition import apply_supported_tactical_discard
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


ORDINARY_REDRAW_BOSSES = (
    "The Arm",
    "The Club",
    "The Eye",
    "Amber Acorn",
    "Crimson Heart",
    "Violet Vessel",
    "The Fish",
    "The Flint",
    "The Goad",
    "The Head",
    "The Hook",
    "The House",
    "The Mouth",
    "The Ox",
    "The Pillar",
    "The Plant",
    "The Tooth",
    "The Wall",
    "The Window",
    "Verdant Leaf",
)


def _boss_run(name: str, *, seed: str | None = None) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 8 if name in {
        "Amber Acorn",
        "Crimson Heart",
        "Violet Vessel",
        "Verdant Leaf",
    } else 2
    state.round = 2
    state.blind = Blind(BlindType.BOSS, requirement=99_999, reward=5)
    state.boss_name = name
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    run = HeadlessRunState(public=state, seed=seed or f"R4-DISCARD-{name}")
    if name == "The Pillar":
        for card in run.require_playing_card_order():
            card.played_this_ante_observed = True
    return select_blind_exact(run)


@pytest.mark.parametrize("boss_name", ORDINARY_REDRAW_BOSSES)
def test_env_r4_audited_ordinary_boss_discard_refills_exactly(boss_name):
    run = _boss_run(boss_name)
    before_rng = run.rng_snapshot()

    result = apply_supported_tactical_discard(run, (0, 2))

    assert len(run.public.hand) == run.public.hand_size == 8
    assert run.public.discards_remaining == 3
    assert run.public.discards_used == 0
    assert len(result.public.hand) == result.public.hand_size == 8
    assert result.public.discards_remaining == 2
    assert result.public.discards_used == 1
    assert len(result.public.discard_pile) == 2
    assert len(result.draw_pile) == 42
    assert result.rng_snapshot() == before_rng
    if boss_name == "The Fish":
        assert all(card.facing_observed for card in result.public.hand)
        assert not any(card.face_down for card in result.public.hand)
    if boss_name == "The House":
        assert sum(card.face_down for card in result.public.hand) == 6
        assert all(card.facing_observed for card in result.public.hand)


@pytest.mark.parametrize(
    "boss_name",
    ("The Serpent", "The Wheel", "The Mark", "Cerulean Bell"),
)
def test_env_r4_special_boss_redraws_remain_fail_closed_atomically(boss_name):
    run = _boss_run(boss_name)
    before = serialize_headless_run_state(run)

    with pytest.raises(HeadlessTransitionError, match=repr(boss_name)):
        apply_supported_tactical_discard(run, (0,))

    assert serialize_headless_run_state(run) == before


def test_env_r4_ordinary_boss_discard_rejects_inexact_resource_state():
    run = _boss_run("The Hook")
    run.public.hand_size = 9
    before = serialize_headless_run_state(run)

    with pytest.raises(HeadlessTransitionError, match="ordinary Red Deck resource"):
        apply_supported_tactical_discard(run, (0,))

    assert serialize_headless_run_state(run) == before


def test_env_r4_mutable_rule_boss_discard_requires_authoritative_state():
    run = _boss_run("The Mouth")
    run.public.boss_blind_state_observed = False
    before = serialize_headless_run_state(run)

    with pytest.raises(HeadlessTransitionError, match="authoritative Boss state"):
        apply_supported_tactical_discard(run, (0,))

    assert serialize_headless_run_state(run) == before
