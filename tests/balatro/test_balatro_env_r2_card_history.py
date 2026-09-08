import pytest

from games.balatro.actions import PLAY_CARDS, BalatroAction
from games.balatro.env.card_history import (
    clear_played_this_ante_for_new_ante,
    initialize_pristine_played_this_ante_history,
    mark_played_cards_this_ante,
)
from games.balatro.env.deal import deal_pristine_round_start
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _fresh_run() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "DRAW_TO_HAND"
    state.hand_size = 8
    return HeadlessRunState(public=state, seed="HISTORY")


def _selecting_run() -> HeadlessRunState:
    initialized = initialize_pristine_played_this_ante_history(_fresh_run())
    return deal_pristine_round_start(initialized)


def _identity(card):
    return card.rank, card.suit


def test_env_r2_pristine_history_initialization_marks_all_cards_observed_false():
    run = _fresh_run()

    result = initialize_pristine_played_this_ante_history(run)

    assert all(
        card.played_this_ante_observed
        for card in result.require_playing_card_order()
    )
    assert not any(card.played_this_ante for card in result.require_playing_card_order())
    assert not any(
        card.played_this_ante_observed
        for card in run.require_playing_card_order()
    )


def test_env_r2_pristine_history_initialization_rejects_live_or_existing_history():
    run = _fresh_run()
    run.require_playing_card_order()[0].live_id = 1
    with pytest.raises(HeadlessTransitionError, match="cannot replace live history"):
        initialize_pristine_played_this_ante_history(run)

    run = _fresh_run()
    run.require_playing_card_order()[0].played_this_ante_observed = True
    with pytest.raises(HeadlessTransitionError, match="uninitialized history"):
        initialize_pristine_played_this_ante_history(run)


def test_env_r2_mark_played_cards_sets_only_selected_permanent_history():
    run = _selecting_run()
    selected = [run.public.hand[0], run.public.hand[3], run.public.hand[-1]]
    selected_ids = {_identity(card) for card in selected}

    result = mark_played_cards_this_ante(
        run,
        BalatroAction(PLAY_CARDS, cards=selected),
    )

    assert {
        _identity(card)
        for card in result.require_playing_card_order()
        if card.played_this_ante
    } == selected_ids
    assert all(
        card.played_this_ante_observed
        for card in result.require_playing_card_order()
    )
    assert not any(card.played_this_ante for card in run.require_playing_card_order())


def test_env_r2_mark_played_cards_preserves_prior_ante_history():
    run = _selecting_run()
    prior = run.public.hand[1]
    prior.played_this_ante = True
    selected = run.public.hand[4]

    result = mark_played_cards_this_ante(
        run,
        BalatroAction(PLAY_CARDS, cards=[selected]),
    )

    marked = {
        _identity(card)
        for card in result.require_playing_card_order()
        if card.played_this_ante
    }
    assert marked == {_identity(prior), _identity(selected)}


def test_env_r2_mark_played_cards_requires_authoritative_history_and_current_hand():
    run = _selecting_run()
    run.require_playing_card_order()[0].played_this_ante_observed = False
    with pytest.raises(HeadlessTransitionError, match="authoritative permanent-card history"):
        mark_played_cards_this_ante(
            run,
            BalatroAction(PLAY_CARDS, cards=[run.public.hand[0]]),
        )

    run = _selecting_run()
    foreign = run.require_playing_card_order()[0]
    if foreign in run.public.hand:
        foreign = next(
            card
            for card in run.require_playing_card_order()
            if card not in run.public.hand
        )
    with pytest.raises(HeadlessTransitionError, match="current-hand cards"):
        mark_played_cards_this_ante(
            run,
            BalatroAction(PLAY_CARDS, cards=[foreign]),
        )


def test_env_r2_mark_played_cards_rejects_wrong_phase_action_and_duplicates():
    run = _selecting_run()
    selected = run.public.hand[0]

    run.public.phase = "DRAW_TO_HAND"
    with pytest.raises(HeadlessTransitionError, match="SELECTING_HAND"):
        mark_played_cards_this_ante(
            run,
            BalatroAction(PLAY_CARDS, cards=[selected]),
        )

    run = _selecting_run()
    selected = run.public.hand[0]
    with pytest.raises(HeadlessTransitionError, match="requires PLAY_CARDS"):
        mark_played_cards_this_ante(
            run,
            BalatroAction("DISCARD_CARDS", cards=[selected]),
        )
    with pytest.raises(HeadlessTransitionError, match="duplicate"):
        mark_played_cards_this_ante(
            run,
            BalatroAction(PLAY_CARDS, cards=[selected, selected]),
        )


def test_env_r2_new_ante_clear_resets_values_but_keeps_history_authoritative():
    run = _selecting_run()
    for card in run.require_playing_card_order()[::7]:
        card.played_this_ante = True

    result = clear_played_this_ante_for_new_ante(run)

    assert all(
        card.played_this_ante_observed
        for card in result.require_playing_card_order()
    )
    assert not any(card.played_this_ante for card in result.require_playing_card_order())
    assert any(card.played_this_ante for card in run.require_playing_card_order())


def test_env_r2_new_ante_clear_fails_closed_on_unknown_history():
    run = _selecting_run()
    run.require_playing_card_order()[-1].played_this_ante_observed = False

    with pytest.raises(HeadlessTransitionError, match="authoritative permanent-card history"):
        clear_played_this_ante_for_new_ante(run)
