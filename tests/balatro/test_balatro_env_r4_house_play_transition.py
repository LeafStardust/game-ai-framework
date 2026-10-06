import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.boss_facing import start_supported_deterministic_facing_boss
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.public_observation import public_observation_state
from games.balatro.env.serialization import serialize_headless_run_state
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


def _house_run(*, seed="R4-HOUSE", requirement=99_999):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 2
    state.round = 3
    state.blind = Blind(BlindType.BOSS, requirement=requirement, reward=5)
    state.boss_name = "The House"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return start_supported_deterministic_facing_boss(
        HeadlessRunState(public=state, seed=seed)
    )


def test_env_r4_house_first_play_reveals_selection_and_draws_replacement_face_up():
    run = _house_run()
    selected = run.public.hand[0]
    selected_identity = (selected.rank, selected.suit)
    expected_score = 5 + BalatroScorer.RANK_CHIPS[selected.rank]
    before = serialize_headless_run_state(run)
    before_rng = run.rng_snapshot()

    result = apply_supported_ordinary_play(run, (0,))

    assert serialize_headless_run_state(run) == before
    assert result.rng_snapshot() == before_rng
    assert result.public.score == expected_score
    assert result.public.hands_remaining == 3
    assert len(result.public.hand) == result.public.hand_size == 8
    assert sum(card.face_down for card in result.public.hand) == 7
    assert all(card.facing_observed for card in result.public.hand)
    assert (result.public.discard_pile[-1].rank, result.public.discard_pile[-1].suit) == (
        selected_identity
    )
    assert result.public.discard_pile[-1].face_down is False
    assert result.public.discard_pile[-1].facing_observed is True


def test_env_r4_house_retained_cards_stay_masked_while_replacement_is_public():
    result = apply_supported_ordinary_play(_house_run(seed="R4-HOUSE-MASK"), (0,))
    observation = public_observation_state(result.public)

    hidden_count = 0
    visible_count = 0
    for internal, public in zip(result.public.hand, observation.hand, strict=True):
        if internal.face_down:
            hidden_count += 1
            assert public.rank == "?"
            assert public.suit == "?"
            assert public.live_id is None
        else:
            visible_count += 1
            assert public.rank == internal.rank
            assert public.suit == internal.suit
    assert hidden_count == 7
    assert visible_count == 1


def test_env_r4_house_later_hidden_play_reveals_before_scoring():
    after_first = apply_supported_ordinary_play(
        _house_run(seed="R4-HOUSE-LATER"),
        (0,),
    )
    hidden_index = next(
        index for index, card in enumerate(after_first.public.hand) if card.face_down
    )
    selected = after_first.public.hand[hidden_index]
    expected_increment = 5 + BalatroScorer.RANK_CHIPS[selected.rank]

    result = apply_supported_ordinary_play(after_first, (hidden_index,))

    assert result.public.score == after_first.public.score + expected_increment
    assert result.public.discard_pile[-1].face_down is False
    assert result.public.discard_pile[-1].facing_observed is True
    assert sum(card.face_down for card in result.public.hand) == 6


@pytest.mark.parametrize("corruption", ["unobserved_hand", "hidden_draw"])
def test_env_r4_house_rejects_inexact_facing_state_atomically(corruption):
    run = _house_run(seed=f"R4-HOUSE-BAD-{corruption}")
    if corruption == "unobserved_hand":
        run.public.hand[0].facing_observed = False
    else:
        run.draw_pile[0].face_down = True
        run.draw_pile[0].facing_observed = True
    before = serialize_headless_run_state(run)
    before_rng = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="House Play"):
        apply_supported_ordinary_play(run, (0,))

    assert serialize_headless_run_state(run) == before
    assert run.rng_snapshot() == before_rng
