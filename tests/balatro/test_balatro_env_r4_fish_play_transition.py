import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.boss_facing import start_supported_fish
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.public_observation import public_observation_state
from games.balatro.env.serialization import serialize_headless_run_state
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


def _fish_run(*, seed="R4-FISH", requirement=99_999):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 5
    state.round = 12
    state.blind = Blind(BlindType.BOSS, requirement=requirement, reward=5)
    state.boss_name = "The Fish"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return start_supported_fish(HeadlessRunState(public=state, seed=seed))


def test_env_r4_fish_play_replenishes_face_down_and_masks_only_public_identity():
    run = _fish_run()
    selected = run.public.hand[0]
    expected_score = 5 + BalatroScorer.RANK_CHIPS[selected.rank]

    result = apply_supported_ordinary_play(run, (0,))
    observation = public_observation_state(result.public)

    assert result.public.score == expected_score
    assert result.public.hands_remaining == 3
    assert len(result.public.hand) == result.public.hand_size == 8
    assert sum(card.face_down for card in result.public.hand) == 1
    assert result.public.discard_pile[-1].face_down is False
    hidden = next(index for index, card in enumerate(result.public.hand) if card.face_down)
    assert observation.hand[hidden].rank == "?"
    assert observation.hand[hidden].suit == "?"
    assert result.public.hand[hidden].rank != "?"
    assert result.public.hand[hidden].suit != "?"


def test_env_r4_fish_hidden_play_reveals_before_scoring_and_hides_replacement():
    after_first = apply_supported_ordinary_play(_fish_run(seed="R4-FISH-HIDDEN"), (0,))
    hidden_index = next(
        index for index, card in enumerate(after_first.public.hand) if card.face_down
    )
    selected = after_first.public.hand[hidden_index]
    expected_increment = 5 + BalatroScorer.RANK_CHIPS[selected.rank]

    result = apply_supported_ordinary_play(after_first, (hidden_index,))

    assert result.public.score == after_first.public.score + expected_increment
    assert result.public.discard_pile[-1].face_down is False
    assert result.public.discard_pile[-1].facing_observed is True
    assert sum(card.face_down for card in result.public.hand) == 1


@pytest.mark.parametrize("corruption", ["unobserved_hand", "hidden_draw"])
def test_env_r4_fish_rejects_inexact_facing_state_atomically(corruption):
    run = _fish_run(seed=f"R4-FISH-BAD-{corruption}")
    if corruption == "unobserved_hand":
        run.public.hand[0].facing_observed = False
    else:
        run.draw_pile[0].face_down = True
        run.draw_pile[0].facing_observed = True
    before = serialize_headless_run_state(run)

    with pytest.raises(HeadlessTransitionError, match="Fish Play"):
        apply_supported_ordinary_play(run, (0,))

    assert serialize_headless_run_state(run) == before
