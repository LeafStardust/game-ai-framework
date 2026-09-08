import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.boss_facing import (
    clear_facing_boss_hand,
    draw_fish_post_discard_cards,
    draw_fish_post_play_cards,
    start_supported_fish,
)
from games.balatro.env.state import EnvStateFrame
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run(seed: str = "FISH") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 4
    state.round = 6
    state.blind = Blind(BlindType.BOSS, requirement=20000)
    state.boss_name = "The Fish"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    state.discards_used = 0
    return HeadlessRunState(public=state, seed=seed)


def _remove_from_hand(run: HeadlessRunState, count: int) -> None:
    del run.public.hand[:count]


def test_env_r2_fish_initial_draw_is_authoritatively_face_up():
    result = start_supported_fish(_run())

    assert result.public.phase == "SELECTING_HAND"
    assert len(result.public.hand) == result.public.hand_size
    assert all(not card.face_down for card in result.public.hand)
    assert all(card.facing_observed for card in result.public.hand)


def test_env_r2_fish_post_play_replenishment_hides_only_newly_drawn_cards():
    run = start_supported_fish(_run("FISH-PLAY"))
    retained = list(run.public.hand[2:])
    retained_creation_ids = {
        index
        for index, card in enumerate(run.require_playing_card_order())
        if id(card) in {id(value) for value in retained}
    }
    _remove_from_hand(run, 2)
    run.public.round_hand_play_counts["PAIR"] = 1

    result = draw_fish_post_play_cards(run)
    result_order = result.require_playing_card_order()

    assert len(result.public.hand) == result.public.hand_size
    assert sum(card.face_down for card in result.public.hand) == 2
    assert all(card.facing_observed for card in result.public.hand)
    for index in retained_creation_ids:
        assert not result_order[index].face_down


def test_env_r2_fish_post_play_hidden_identity_is_masked_but_retained_internally():
    run = start_supported_fish(_run("FISH-MASK"))
    _remove_from_hand(run, 3)
    run.public.round_hand_play_counts["HIGH_CARD"] = 1

    result = draw_fish_post_play_cards(run)
    observation = EnvStateFrame(state=result.public).observation()

    assert sum(card.face_down for card in result.public.hand) == 3
    for internal, public in zip(result.public.hand, observation.hand, strict=True):
        if internal.face_down:
            assert internal.rank != "?"
            assert internal.suit != "?"
            assert public.rank == "?"
            assert public.suit == "?"
            assert public.live_id is None
        else:
            assert public.rank == internal.rank
            assert public.suit == internal.suit


def test_env_r2_fish_post_discard_draws_face_up_and_preserves_older_hidden_cards():
    run = start_supported_fish(_run("FISH-DISCARD"))
    _remove_from_hand(run, 2)
    run.public.round_hand_play_counts["PAIR"] = 1
    after_play = draw_fish_post_play_cards(run)

    hidden_before = [card for card in after_play.public.hand if card.face_down]
    assert len(hidden_before) == 2
    kept_hidden = hidden_before[0]
    kept_index = next(
        index
        for index, card in enumerate(after_play.require_playing_card_order())
        if card is kept_hidden
    )

    # Model a later discard boundary: one card left the hand and the canonical
    # public discard-use counter has already advanced before replenishment.
    after_play.public.hand.remove(hidden_before[1])
    after_play.public.discards_used = 1

    result = draw_fish_post_discard_cards(after_play)
    result_order = result.require_playing_card_order()

    assert len(result.public.hand) == result.public.hand_size
    assert result_order[kept_index].face_down
    assert sum(card.face_down for card in result.public.hand) == 1
    assert all(card.facing_observed for card in result.public.hand)


def test_env_r2_fish_replenishment_respects_capacity_and_empty_deck():
    run = start_supported_fish(_run("FISH-CAP"))
    run.public.round_hand_play_counts["PAIR"] = 1

    full = draw_fish_post_play_cards(run)
    assert len(full.public.hand) == run.public.hand_size

    run = start_supported_fish(_run("FISH-SHORT"))
    run.public.round_hand_play_counts["PAIR"] = 1
    _remove_from_hand(run, 3)
    # Preserve exact public/private composition while making only one physical
    # future card available to this narrow draw boundary.
    keep = run.draw_pile[-1:]
    keep_ids = {id(card) for card in keep}
    run.draw_pile = keep
    run.public.deck = [card for card in run.public.deck if id(card) in keep_ids]

    short = draw_fish_post_play_cards(run)
    assert len(short.public.hand) == 6
    assert sum(card.face_down for card in short.public.hand) == 1


def test_env_r2_fish_temporal_helpers_require_exact_action_evidence():
    run = start_supported_fish(_run("FISH-EVIDENCE"))
    _remove_from_hand(run, 1)

    with pytest.raises(HeadlessTransitionError, match="played hand"):
        draw_fish_post_play_cards(run)

    with pytest.raises(HeadlessTransitionError, match="discard"):
        draw_fish_post_discard_cards(run)


def test_env_r2_fish_draws_isolate_input_and_consume_no_rng():
    run = start_supported_fish(_run("FISH-ISOLATE"))
    _remove_from_hand(run, 2)
    run.public.round_hand_play_counts["PAIR"] = 1
    before_hand = list(run.public.hand)
    before_draw = list(run.draw_pile)
    before_rng = run.rng_snapshot()

    result = draw_fish_post_play_cards(run)

    assert result is not run
    assert run.public.hand == before_hand
    assert run.draw_pile == before_draw
    assert run.rng_snapshot() == before_rng
    assert result.rng_snapshot() == before_rng


def test_env_r2_fish_cleanup_flips_remaining_hidden_hand_up_without_rng():
    run = start_supported_fish(_run("FISH-CLEAN"))
    _remove_from_hand(run, 2)
    run.public.round_hand_play_counts["PAIR"] = 1
    run = draw_fish_post_play_cards(run)
    before_rng = run.rng_snapshot()

    result = clear_facing_boss_hand(run)

    assert all(not card.face_down for card in result.public.hand)
    assert all(card.facing_observed for card in result.public.hand)
    assert result.rng_snapshot() == before_rng
