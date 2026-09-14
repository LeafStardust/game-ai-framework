import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import start_supported_pillar
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.serialization import serialize_headless_run_state
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


def _pillar_run(*, seed="R4-PILLAR", requirement=99_999):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 3
    state.round = 6
    state.blind = Blind(BlindType.BOSS, requirement=requirement, reward=5)
    state.boss_name = "The Pillar"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    run = HeadlessRunState(public=state, seed=seed)
    for card in run.require_playing_card_order():
        card.played_this_ante_observed = True
    return start_supported_pillar(run)


def test_env_r4_pillar_play_scores_hand_base_but_not_debuffed_card_chips():
    run = _pillar_run()
    selected = run.public.hand[0]
    selected.played_this_ante = True
    selected.debuffed = True
    rng_before = run.rng_snapshot()

    result = apply_supported_ordinary_play(run, (0,))

    assert result.public.score == 5
    assert result.public.hands_remaining == 3
    assert result.public.phase == "SELECTING_HAND"
    assert result.public.discard_pile[-1].debuffed is True
    assert result.public.discard_pile[-1].played_this_ante is True
    assert result.rng_snapshot() == rng_before
    assert run.public.score == 0
    assert run.public.hands_remaining == 4


def test_env_r4_pillar_accepts_newly_played_clean_history_only_after_discard_movement():
    run = _pillar_run(seed="R4-PILLAR-NEW")
    first = run.public.hand[0]
    first_score = 5 + BalatroScorer.RANK_CHIPS[first.rank]

    after_first = apply_supported_ordinary_play(run, (0,))
    assert after_first.public.discard_pile[-1].played_this_ante is True
    assert after_first.public.discard_pile[-1].debuffed is False

    second = after_first.public.hand[0]
    result = apply_supported_ordinary_play(after_first, (0,))

    assert result.public.score == (
        first_score + 5 + BalatroScorer.RANK_CHIPS[second.rank]
    )
    assert result.public.hands_remaining == 2


@pytest.mark.parametrize(
    "history, debuffed, message",
    [
        (False, True, "debuff outside owned Ante history"),
        (True, False, "incomplete active history debuffs"),
    ],
)
def test_env_r4_pillar_rejects_inconsistent_active_debuff_state_atomically(
    history,
    debuffed,
    message,
):
    run = _pillar_run(seed=f"R4-PILLAR-BAD-{history}-{debuffed}")
    run.public.hand[0].played_this_ante = history
    run.public.hand[0].debuffed = debuffed
    before = serialize_headless_run_state(run)

    with pytest.raises(HeadlessTransitionError, match=message):
        apply_supported_ordinary_play(run, (0,))

    assert serialize_headless_run_state(run) == before
