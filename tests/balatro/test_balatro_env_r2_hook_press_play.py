import pytest

from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import start_supported_start_inert_boss
from games.balatro.env.boss_play import apply_hook_press_play_discards
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _hook_run(*, hand_size: int = 8, seed: str = "HOOK") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 4
    state.round = 6
    state.blind = Blind(BlindType.BOSS, requirement=20000)
    state.boss_name = "The Hook"
    state.hand_size = hand_size
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    state.hands_remaining = 1
    state.discards_remaining = 1
    return HeadlessRunState(public=state, seed=seed)


def _identity(card):
    return card.rank, card.suit, card.live_id


def test_env_r2_hook_start_is_inert_until_press_play():
    started = start_supported_start_inert_boss(_hook_run())

    assert started.public.phase == "SELECTING_HAND"
    assert len(started.public.hand) == 8
    assert started.public.discard_pile == []
    assert started.discard_pile == []
    assert "hook" not in started.rng.nodes


def test_env_r2_hook_forces_two_discards_from_remaining_not_played_cards():
    started = start_supported_start_inert_boss(_hook_run())
    played = list(started.public.hand[:5])
    played_identities = {_identity(card) for card in played}
    action = BalatroAction(PLAY_CARDS, cards=played)
    before_draw = [_identity(card) for card in started.draw_pile]
    before_deck = [_identity(card) for card in started.public.deck]
    before_discards = started.public.discards_remaining

    result = apply_hook_press_play_discards(started, action)

    discarded = {_identity(card) for card in result.discard_pile}
    assert len(discarded) == 2
    assert discarded.isdisjoint(played_identities)
    # This helper owns only the Boss mutation. The ordinary hand→play movement
    # remains for the later tactical transition, so chosen play cards stay here.
    assert played_identities.issubset({_identity(card) for card in result.public.hand})
    assert len(result.public.hand) == 6
    assert [_identity(card) for card in result.public.discard_pile] == [
        _identity(card) for card in result.discard_pile
    ]
    assert result.public.discards_remaining == before_discards
    assert [_identity(card) for card in result.draw_pile] == before_draw
    assert [_identity(card) for card in result.public.deck] == before_deck
    assert result.public.phase == "SELECTING_HAND"


def test_env_r2_hook_consumes_two_keyed_draws_and_is_replay_deterministic():
    started_a = start_supported_start_inert_boss(_hook_run(seed="HOOK-REPLAY"))
    started_b = start_supported_start_inert_boss(_hook_run(seed="HOOK-REPLAY"))
    before_rng = started_a.rng_snapshot()

    result_a = apply_hook_press_play_discards(
        started_a,
        BalatroAction(PLAY_CARDS, cards=list(started_a.public.hand[:3])),
    )
    result_b = apply_hook_press_play_discards(
        started_b,
        BalatroAction(PLAY_CARDS, cards=list(started_b.public.hand[:3])),
    )

    assert [_identity(card) for card in result_a.discard_pile] == [
        _identity(card) for card in result_b.discard_pile
    ]
    assert result_a.rng_snapshot() == result_b.rng_snapshot()
    assert result_a.rng_snapshot() != before_rng
    assert "hook" in result_a.rng.nodes
    assert started_a.rng_snapshot() == before_rng


def test_env_r2_hook_discards_only_one_when_only_one_candidate_remains():
    started = start_supported_start_inert_boss(_hook_run(hand_size=5))
    played = list(started.public.hand[:4])

    result = apply_hook_press_play_discards(
        started,
        BalatroAction(PLAY_CARDS, cards=played),
    )

    assert len(result.discard_pile) == 1
    assert len(result.public.hand) == 4


def test_env_r2_hook_candidate_seal_lifecycle_fails_closed_without_rng_mutation():
    started = start_supported_start_inert_boss(_hook_run())
    played = list(started.public.hand[:5])
    candidate = started.public.hand[5]
    candidate.seal = "Purple"
    before_rng = started.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="sealed discard candidates"):
        apply_hook_press_play_discards(
            started,
            BalatroAction(PLAY_CARDS, cards=played),
        )

    assert started.rng_snapshot() == before_rng
    assert started.public.discard_pile == []
    assert started.discard_pile == []


def test_env_r2_hook_input_state_is_isolated():
    started = start_supported_start_inert_boss(_hook_run())
    before_hand = [_identity(card) for card in started.public.hand]
    before_rng = started.rng_snapshot()

    result = apply_hook_press_play_discards(
        started,
        BalatroAction(PLAY_CARDS, cards=list(started.public.hand[:2])),
    )

    assert result is not started
    assert [_identity(card) for card in started.public.hand] == before_hand
    assert started.public.discard_pile == []
    assert started.discard_pile == []
    assert started.rng_snapshot() == before_rng
