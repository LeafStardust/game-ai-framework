import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import (
    prepare_supported_mutable_hand_rule_boss_start,
    start_supported_mutable_hand_rule_boss,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.burglar import BurglarJoker
from games.balatro.state import BalatroState


def _run(*, boss_name: str, requirement: int = 10000) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 4
    state.round = 9
    state.blind = Blind(BlindType.BOSS, requirement)
    state.boss_name = boss_name
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    # Seed deliberately stale mutable state to prove Blind:set_blind replacement.
    state.boss_blind_state_observed = True
    state.boss_blind_hands = {"PAIR", "FLUSH"}
    state.boss_blind_only_hand = "STRAIGHT"
    return HeadlessRunState(public=state, seed="HAND-RULE-BOSS")


@pytest.mark.parametrize("boss_name", ["The Eye", "The Mouth"])
def test_env_r2_mutable_hand_rule_boss_initializes_exact_empty_start_state(boss_name):
    run = _run(boss_name=boss_name)
    before_rng = run.rng_snapshot()

    result = prepare_supported_mutable_hand_rule_boss_start(run)

    assert result is not run
    assert run.public.round == 9
    assert run.public.boss_blind_hands == {"PAIR", "FLUSH"}
    assert run.public.boss_blind_only_hand == "STRAIGHT"

    assert result.public.phase == "DRAW_TO_HAND"
    assert result.public.round == 10
    assert result.public.blind_score == 10000
    assert result.public.hands_remaining == 4
    assert result.public.discards_remaining == 3
    assert result.public.boss_blind_state_observed is True
    assert result.public.boss_blind_hands == set()
    assert result.public.boss_blind_only_hand is None
    assert result.rng_snapshot() == before_rng


def test_env_r2_eye_start_orders_round_bonus_then_mutable_state_then_burglar():
    run = _run(boss_name="The Eye")
    run.round_bonus_hands = 2
    run.round_bonus_discards = -1
    run.public.jokers = [BurglarJoker()]

    result = prepare_supported_mutable_hand_rule_boss_start(run)

    # Baseline is 4+2=6 hands and 3-1=2 discards; Eye initializes its table;
    # Burglar then adds 3 hands and forces discards to zero.
    assert result.public.hands_remaining == 9
    assert result.public.discards_remaining == 0
    assert result.public.boss_blind_state_observed is True
    assert result.public.boss_blind_hands == set()
    assert result.round_bonus_hands == 0
    assert result.round_bonus_discards == 0


def test_env_r2_mouth_start_composes_with_exact_shuffle_deal():
    run = _run(boss_name="The Mouth", requirement=12000)

    result = start_supported_mutable_hand_rule_boss(run)

    assert result.public.phase == "SELECTING_HAND"
    assert result.public.blind_score == 12000
    assert result.public.boss_blind_state_observed is True
    assert result.public.boss_blind_only_hand is None
    assert len(result.public.hand) == 8
    assert len(result.draw_pile) == 44
    assert "nr4" in result.rng.nodes


@pytest.mark.parametrize("boss_name", ["The Wall", "Violet Vessel", "The Water", "The Needle"])
def test_env_r2_mutable_hand_rule_boss_gate_rejects_other_bosses(boss_name):
    run = _run(boss_name=boss_name)

    with pytest.raises(HeadlessTransitionError, match="mutable hand-rule start set"):
        prepare_supported_mutable_hand_rule_boss_start(run)


def test_env_r2_mutable_hand_rule_boss_keeps_tags_and_vouchers_fail_closed():
    run = _run(boss_name="The Eye")
    run.tags.append("DOUBLE")
    with pytest.raises(HeadlessTransitionError, match="active tags"):
        prepare_supported_mutable_hand_rule_boss_start(run)

    run = _run(boss_name="The Mouth")
    run.public.vouchers.append("Grabber")
    with pytest.raises(HeadlessTransitionError, match="vouchers"):
        prepare_supported_mutable_hand_rule_boss_start(run)
