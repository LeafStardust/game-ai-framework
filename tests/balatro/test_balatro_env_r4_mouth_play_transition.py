import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import start_supported_mutable_hand_rule_boss
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.serialization import (
    restore_headless_run_state,
    serialize_headless_run_state,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


def _mouth_run(*, seed="R4-MOUTH", requirement=99_999):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 6
    state.round = 15
    state.blind = Blind(BlindType.BOSS, requirement=requirement, reward=5)
    state.boss_name = "The Mouth"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return start_supported_mutable_hand_rule_boss(
        HeadlessRunState(public=state, seed=seed)
    )


def test_env_r4_mouth_first_hand_locks_and_same_type_scores_after_restore():
    run = _mouth_run()
    first = run.public.hand[0]
    first_score = 5 + BalatroScorer.RANK_CHIPS[first.rank]

    locked = apply_supported_ordinary_play(run, (0,))
    restored = restore_headless_run_state(serialize_headless_run_state(locked))
    second = restored.public.hand[0]
    result = apply_supported_ordinary_play(restored, (0,))

    assert locked.public.boss_blind_only_hand == "HIGH_CARD"
    assert locked.public.boss_blind_state_observed is True
    assert locked.public.score == first_score
    assert result.public.boss_blind_only_hand == "HIGH_CARD"
    assert result.public.score == first_score + 5 + BalatroScorer.RANK_CHIPS[second.rank]
    assert run.public.boss_blind_only_hand is None


def test_env_r4_mouth_different_type_scores_zero_without_replacing_lock():
    run = _mouth_run(seed="R4-MOUTH-REJECT")
    run.public.boss_blind_only_hand = "PAIR"
    before = serialize_headless_run_state(run)

    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.last_played_hand == "HIGH_CARD"
    assert result.public.boss_blind_only_hand == "PAIR"
    assert result.public.score == 0
    assert result.public.hands_remaining == 3
    assert serialize_headless_run_state(run) == before


@pytest.mark.parametrize("field, value", [
    ("boss_blind_state_observed", False),
    ("boss_blind_only_hand", "Pair"),
])
def test_env_r4_mouth_rejects_inexact_mutable_state_atomically(field, value):
    run = _mouth_run(seed=f"R4-MOUTH-BAD-{field}")
    setattr(run.public, field, value)
    before = serialize_headless_run_state(run)

    with pytest.raises(HeadlessTransitionError, match="Mouth Play"):
        apply_supported_ordinary_play(run, (0,))

    assert serialize_headless_run_state(run) == before
