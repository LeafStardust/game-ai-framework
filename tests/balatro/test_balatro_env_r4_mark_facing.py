import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.boss_facing import start_supported_deterministic_facing_boss
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.public_observation import public_observation_state
from games.balatro.env.serialization import serialize_headless_run_state
from games.balatro.env.tactical_transition import apply_supported_tactical_discard
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


def _mark_run(*, seed="R4-MARK", requirement=99_999):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 2
    state.round = 3
    state.blind = Blind(BlindType.BOSS, requirement=requirement, reward=5)
    state.boss_name = "The Mark"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return start_supported_deterministic_facing_boss(
        HeadlessRunState(public=state, seed=seed)
    )


def _creation_indices(run):
    return {
        id(card): index
        for index, card in enumerate(run.require_playing_card_order())
    }


def test_env_r4_mark_discard_faces_only_physical_face_card_replacements():
    run = _mark_run(seed="R4-MARK-DISCARD")
    before = serialize_headless_run_state(run)
    before_rng = run.rng_snapshot()
    creation_index = _creation_indices(run)
    selected_indices = (0, 2, 4)
    replacement_indices = [
        creation_index[id(run.draw_pile[-1 - offset])]
        for offset in range(len(selected_indices))
    ]
    expected_replacement_facing = [
        run.require_playing_card_order()[index].rank in {"J", "Q", "K"}
        for index in replacement_indices
    ]
    retained_facing = {
        creation_index[id(card)]: card.face_down
        for offset, card in enumerate(run.public.hand)
        if offset not in selected_indices
    }

    result = apply_supported_tactical_discard(run, selected_indices)
    result_order = result.require_playing_card_order()

    assert serialize_headless_run_state(run) == before
    assert result.rng_snapshot() == before_rng
    assert result.public.discards_remaining == 2
    assert result.public.discards_used == 1
    assert len(result.public.hand) == result.public.hand_size == 8
    assert [
        result_order[index].face_down for index in replacement_indices
    ] == expected_replacement_facing
    assert all(result_order[index].facing_observed for index in replacement_indices)
    assert {
        index: result_order[index].face_down for index in retained_facing
    } == retained_facing

    observation = public_observation_state(result.public)
    for internal, public in zip(result.public.hand, observation.hand, strict=True):
        if internal.face_down:
            assert (public.rank, public.suit, public.live_id) == ("?", "?", None)
        else:
            assert (public.rank, public.suit) == (internal.rank, internal.suit)


def test_env_r4_mark_play_reveals_selected_face_before_scoring_and_refills_exactly():
    run = _mark_run(seed="R4-MARK-PLAY")
    hidden_index = next(
        index for index, card in enumerate(run.public.hand) if card.face_down
    )
    selected = run.public.hand[hidden_index]
    expected_score = 5 + BalatroScorer.RANK_CHIPS[selected.rank]
    before = serialize_headless_run_state(run)
    before_rng = run.rng_snapshot()
    creation_index = _creation_indices(run)
    replacement_index = creation_index[id(run.draw_pile[-1])]
    replacement_should_hide = (
        run.require_playing_card_order()[replacement_index].rank in {"J", "Q", "K"}
    )

    result = apply_supported_ordinary_play(run, (hidden_index,))
    result_order = result.require_playing_card_order()

    assert serialize_headless_run_state(run) == before
    assert result.rng_snapshot() == before_rng
    assert result.public.score == expected_score
    assert result.public.hands_remaining == 3
    assert len(result.public.hand) == result.public.hand_size == 8
    assert result.public.discard_pile[-1].face_down is False
    assert result.public.discard_pile[-1].facing_observed is True
    assert result_order[replacement_index].face_down is replacement_should_hide
    assert result_order[replacement_index].facing_observed is True


def test_env_r4_mark_discard_rejects_resource_drift_atomically():
    run = _mark_run(seed="R4-MARK-DISCARD-BAD-RESOURCE")
    run.public.hand_size += 1
    before = serialize_headless_run_state(run)
    before_rng = run.rng_snapshot()

    with pytest.raises(
        HeadlessTransitionError,
        match="Mark discard requires ordinary Red Deck resource state",
    ):
        apply_supported_tactical_discard(run, (0,))

    assert serialize_headless_run_state(run) == before
    assert run.rng_snapshot() == before_rng


@pytest.mark.parametrize("corruption", ["unobserved_hand", "hidden_draw", "resource"])
def test_env_r4_mark_rejects_inexact_transition_state_atomically(corruption):
    run = _mark_run(seed=f"R4-MARK-BAD-{corruption}")
    if corruption == "unobserved_hand":
        run.public.hand[0].facing_observed = False
    elif corruption == "hidden_draw":
        run.draw_pile[0].face_down = True
        run.draw_pile[0].facing_observed = True
    else:
        run.public.hand_size += 1
    before = serialize_headless_run_state(run)
    before_rng = run.rng_snapshot()

    expected = "Mark Play" if corruption != "resource" else "Voucher hand size"
    with pytest.raises(HeadlessTransitionError, match=expected):
        apply_supported_ordinary_play(run, (0,))

    assert serialize_headless_run_state(run) == before
    assert run.rng_snapshot() == before_rng
