import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.boss_facing import (
    _DETERMINISTIC_FACING_BOSS_NAMES,
    clear_facing_boss_hand,
    deterministic_card_stays_face_down,
    start_supported_deterministic_facing_boss,
)
from games.balatro.env.state import EnvStateFrame
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.pareidolia import PareidoliaJoker
from games.balatro.state import BalatroState


def _run(boss_name: str, *, seed: str = "FACING") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 4
    state.round = 6
    state.blind = Blind(BlindType.BOSS, requirement=20000)
    state.boss_name = boss_name
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    state.discards_used = 0
    return HeadlessRunState(public=state, seed=seed)


def test_env_r2_house_initial_hand_is_face_down_and_policy_identity_is_masked():
    result = start_supported_deterministic_facing_boss(_run("The House"))

    assert result.public.phase == "SELECTING_HAND"
    assert len(result.public.hand) == result.public.hand_size
    assert all(card.face_down for card in result.public.hand)
    assert all(card.facing_observed for card in result.public.hand)

    observation = EnvStateFrame(state=result.public).observation()
    assert all(card.face_down for card in observation.hand)
    assert all(card.rank == "?" and card.suit == "?" for card in observation.hand)
    assert all(card.live_id is None for card in observation.hand)

    # Hidden observation masking must never erase simulator-owned identity.
    assert all(card.rank != "?" and card.suit != "?" for card in result.public.hand)


def test_env_r2_house_later_draw_predicate_turns_face_up_after_play_or_discard():
    state = _run("The House").public
    card = state.deck[0]

    state.round_hand_play_counts = {key: 0 for key in state.round_hand_play_counts}
    state.discards_used = 0
    assert deterministic_card_stays_face_down(state, card)

    state.round_hand_play_counts["PAIR"] = 1
    assert not deterministic_card_stays_face_down(state, card)

    state.round_hand_play_counts["PAIR"] = 0
    state.discards_used = 1
    assert not deterministic_card_stays_face_down(state, card)


def test_env_r2_house_requires_exact_discard_and_play_history():
    state = _run("The House").public
    card = state.deck[0]

    state.discards_used = None
    with pytest.raises(HeadlessTransitionError, match="discard history"):
        deterministic_card_stays_face_down(state, card)

    state.discards_used = 0
    state.round_hand_play_counts["PAIR"] = True
    with pytest.raises(HeadlessTransitionError, match="hand history"):
        deterministic_card_stays_face_down(state, card)


def test_env_r2_mark_initial_hand_hides_only_face_cards_without_pareidolia():
    result = start_supported_deterministic_facing_boss(_run("The Mark"))

    hidden = [card for card in result.public.hand if card.face_down]
    visible = [card for card in result.public.hand if not card.face_down]

    assert all(card.facing_observed for card in result.public.hand)
    assert all(card.rank in {"J", "Q", "K"} for card in hidden)
    assert all(card.rank not in {"J", "Q", "K"} for card in visible)


def test_env_r2_mark_honors_pareidolia_boss_face_semantics():
    run = _run("The Mark")
    run.public.jokers = [PareidoliaJoker()]

    result = start_supported_deterministic_facing_boss(run)

    assert result.public.hand
    assert all(card.face_down for card in result.public.hand)
    assert all(card.facing_observed for card in result.public.hand)


def test_env_r2_facing_cleanup_flips_remaining_hand_up_without_rng():
    run = start_supported_deterministic_facing_boss(_run("The House"))
    before_rng = run.rng_snapshot()

    result = clear_facing_boss_hand(run)

    assert result is not run
    assert all(card.face_down for card in run.public.hand)
    assert all(not card.face_down for card in result.public.hand)
    assert all(card.facing_observed for card in result.public.hand)
    assert result.rng_snapshot() == before_rng


def test_env_r2_deterministic_facing_start_rejects_wheel_fish_and_unknown():
    assert _DETERMINISTIC_FACING_BOSS_NAMES == frozenset({"The House", "The Mark"})

    for boss_name in ("The Wheel", "The Fish", "Unknown Boss"):
        with pytest.raises(HeadlessTransitionError, match="deterministic facing"):
            start_supported_deterministic_facing_boss(_run(boss_name))
