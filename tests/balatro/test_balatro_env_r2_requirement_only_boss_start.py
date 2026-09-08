import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import (
    prepare_supported_requirement_only_boss_start,
    start_supported_requirement_only_boss,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.burglar import BurglarJoker
from games.balatro.state import BalatroState


def _run(*, boss_name: str, requirement: int, ante: int = 8) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = ante
    state.round = 20
    state.blind = Blind(BlindType.BOSS, requirement)
    state.boss_name = boss_name
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return HeadlessRunState(public=state, seed="REQ-BOSS")


def test_env_r2_violet_vessel_uses_authoritative_enlarged_requirement_only():
    run = _run(boss_name="Violet Vessel", requirement=600000)
    before_rng = run.rng_snapshot()

    result = prepare_supported_requirement_only_boss_start(run)

    assert result.public.phase == "DRAW_TO_HAND"
    assert result.public.round == 21
    assert result.public.blind_score == 600000
    assert result.public.hands_remaining == 4
    assert result.public.discards_remaining == 3
    assert result.rng_snapshot() == before_rng


def test_env_r2_violet_vessel_composes_burglar_then_exact_shuffle_deal():
    run = _run(boss_name="Violet Vessel", requirement=600000)
    run.public.jokers = [BurglarJoker()]

    result = start_supported_requirement_only_boss(run)

    assert result.public.phase == "SELECTING_HAND"
    assert result.public.blind_score == 600000
    assert result.public.hands_remaining == 7
    assert result.public.discards_remaining == 0
    assert len(result.public.hand) == 8
    assert len(result.draw_pile) == 44
    assert "nr8" in result.rng.nodes


@pytest.mark.parametrize("boss_name", ["The Water", "The Needle", "The Eye", "Amber Acorn"])
def test_env_r2_requirement_only_boss_gate_rejects_bosses_with_other_start_semantics(boss_name):
    run = _run(boss_name=boss_name, requirement=10000)

    with pytest.raises(HeadlessTransitionError, match="requirement-only start set"):
        prepare_supported_requirement_only_boss_start(run)


def test_env_r2_requirement_only_boss_gate_requires_actual_boss_blind():
    run = _run(boss_name="Violet Vessel", requirement=600000)
    run.public.blind = Blind(BlindType.BIG, 600000)

    with pytest.raises(HeadlessTransitionError, match="Boss Blind"):
        prepare_supported_requirement_only_boss_start(run)
