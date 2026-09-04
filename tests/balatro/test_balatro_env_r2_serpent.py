import pytest

from games.balatro.env.deal import (
    _hand_sort_key,
    _is_provably_base_order_allowing_transient_debuff,
    _public_card_sort_key,
    deal_supported_round_start,
)
from games.balatro.env.serpent_draw import draw_serpent_post_action_cards
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _dealt_run() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "DRAW_TO_HAND"
    state.boss_name = "The Serpent"
    run = HeadlessRunState(public=state, seed="SERPENT")
    return deal_supported_round_start(run)


def _after_one_play() -> HeadlessRunState:
    run = _dealt_run()
    played = run.public.hand.pop()
    run.played_pile.append(played)
    run.public.round_hand_play_counts["PAIR"] = 1
    return run


def test_env_r2_serpent_draws_three_even_when_that_exceeds_hand_capacity():
    run = _after_one_play()
    assert len(run.public.hand) == run.public.hand_size - 1
    before_rng = run.rng_snapshot()

    result = draw_serpent_post_action_cards(run)

    assert len(result.public.hand) == run.public.hand_size + 2
    assert len(result.draw_pile) == len(run.draw_pile) - 3
    assert result.rng_snapshot() == before_rng
    assert run.rng_snapshot() == before_rng


def test_env_r2_serpent_draws_only_remaining_cards_when_fewer_than_three():
    for remaining in (0, 1, 2):
        run = _after_one_play()
        kept = list(run.draw_pile[-remaining:]) if remaining else []
        run.draw_pile = kept
        run.public.deck = sorted(kept, key=_public_card_sort_key)
        before_hand = len(run.public.hand)

        result = draw_serpent_post_action_cards(run)

        assert len(result.public.hand) == before_hand + remaining
        assert result.draw_pile == []
        assert result.public.deck == []


def test_env_r2_serpent_draw_keeps_physical_order_private_and_public_composition_exact():
    run = _after_one_play()

    result = draw_serpent_post_action_cards(run)

    assert len(result.draw_pile) == len(result.public.deck)
    assert {id(card) for card in result.draw_pile} == {
        id(card) for card in result.public.deck
    }
    assert result.public.deck == sorted(result.draw_pile, key=_public_card_sort_key)


def test_env_r2_serpent_resorts_hand_with_exact_vanilla_owned_card_order():
    run = _after_one_play()

    result = draw_serpent_post_action_cards(run)

    order = result.require_playing_card_order()
    creation_index = {id(card): index for index, card in enumerate(order)}
    pristine = _is_provably_base_order_allowing_transient_debuff(order)
    assert result.public.hand == sorted(
        result.public.hand,
        key=lambda card: _hand_sort_key(
            card,
            pristine=pristine,
            creation_index=creation_index,
        ),
        reverse=True,
    )


def test_env_r2_serpent_discard_history_alone_activates_override():
    run = _dealt_run()
    discarded = run.public.hand.pop()
    run.public.discard_pile.append(discarded)
    run.discard_pile.append(discarded)
    run.public.discards_used = 1

    result = draw_serpent_post_action_cards(run)

    assert len(result.public.hand) == run.public.hand_size + 2


def test_env_r2_serpent_inactive_or_unknown_history_fails_closed():
    run = _dealt_run()
    run.public.discards_used = 0
    with pytest.raises(HeadlessTransitionError, match="inactive before"):
        draw_serpent_post_action_cards(run)

    run = _dealt_run()
    assert run.public.discards_used is None
    with pytest.raises(HeadlessTransitionError, match="authoritative current-round"):
        draw_serpent_post_action_cards(run)

    run = _dealt_run()
    run.public.discards_used = 0
    run.public.round_hand_play_counts["PAIR"] = True
    with pytest.raises(HeadlessTransitionError, match="authoritative current-round"):
        draw_serpent_post_action_cards(run)


def test_env_r2_serpent_positive_discard_proof_is_sufficient_when_hand_counts_are_inexact():
    run = _dealt_run()
    run.public.round_hand_play_counts["PAIR"] = True
    run.public.discards_used = 1

    result = draw_serpent_post_action_cards(run)

    assert len(result.public.hand) == run.public.hand_size + 3


def test_env_r2_serpent_disabled_boss_defers_to_ordinary_draw_semantics():
    run = _after_one_play()
    ChicotJoker = type("ChicotJoker", (), {})
    run.public.jokers.append(ChicotJoker())

    with pytest.raises(HeadlessTransitionError, match="ordinary draw semantics"):
        draw_serpent_post_action_cards(run)


def test_env_r2_serpent_rejects_wrong_phase_identity_and_private_deck_mismatch():
    run = _after_one_play()
    run.public.phase = "SHOP"
    with pytest.raises(HeadlessTransitionError, match="SELECTING_HAND"):
        draw_serpent_post_action_cards(run)

    run = _after_one_play()
    run.public.boss_name = "The Hook"
    with pytest.raises(HeadlessTransitionError, match="requires The Serpent"):
        draw_serpent_post_action_cards(run)

    run = _after_one_play()
    run.draw_pile.pop()
    with pytest.raises(HeadlessTransitionError, match="size disagree"):
        draw_serpent_post_action_cards(run)


def test_env_r2_serpent_isolates_input_state_and_rng():
    run = _after_one_play()
    before_hand = list(run.public.hand)
    before_public_deck = list(run.public.deck)
    before_private_deck = list(run.draw_pile)
    before_rng = run.rng_snapshot()

    result = draw_serpent_post_action_cards(run)

    assert result is not run
    assert run.public.hand == before_hand
    assert run.public.deck == before_public_deck
    assert run.draw_pile == before_private_deck
    assert run.rng_snapshot() == before_rng
