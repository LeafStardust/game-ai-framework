import pytest

from games.balatro.blinds.blind import create_big_blind, create_small_blind
from games.balatro.env.blind_start import (
    prepare_supported_nonboss_blind_start,
    start_supported_nonboss_blind_pristine_deck,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.joker import Joker, JokerContext
from games.balatro.jokers.burglar import BurglarJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.state import BalatroState


class _UnsupportedBlindStartJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        return context


def _run(*, big: bool = False, seed: str = "BURGLAR") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 2
    state.round = 3
    state.blind = create_big_blind(675) if big else create_small_blind(450)
    state.score = 999
    state.hands_remaining = 1
    state.discards_remaining = 1
    state.discards_used = 2
    state.last_played_hand = "PAIR"
    state.round_hand_play_counts["PAIR"] = 3
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return HeadlessRunState(public=state, seed=seed)


def test_env_r2_nonboss_blind_start_applies_round_bonus_then_burglar_then_consumes_bonus():
    run = _run()
    run.public.jokers = [FlatMultJoker(), BurglarJoker()]
    run.round_bonus_hands = 2
    run.round_bonus_discards = -1
    before_rng = run.rng_snapshot()

    result = prepare_supported_nonboss_blind_start(run)

    assert result is not run
    assert run.public.phase == "BLIND_SELECT"
    assert run.public.round == 3
    assert run.round_bonus_hands == 2
    assert run.round_bonus_discards == -1

    assert result.public.phase == "DRAW_TO_HAND"
    assert result.public.round == 4
    assert result.public.blind_score == 450
    # Baseline: 4 reset + 2 one-shot bonus = 6 hands. Burglar then adds 3.
    assert result.public.hands_remaining == 9
    # Baseline would be 3 + (-1) = 2 discards. Burglar then forces zero.
    assert result.public.discards_remaining == 0
    assert result.public.discards_used == 0
    assert result.public.score == 0
    assert result.public.last_played_hand is None
    assert all(value == 0 for value in result.public.round_hand_play_counts.values())
    assert result.round_bonus_hands == 0
    assert result.round_bonus_discards == 0
    assert result.rng_snapshot() == before_rng


def test_env_r2_nonboss_big_blind_burglar_composes_with_exact_pristine_shuffle_and_draw():
    run = _run(big=True)
    run.public.jokers = [BurglarJoker()]

    result = start_supported_nonboss_blind_pristine_deck(run)

    assert result.public.phase == "SELECTING_HAND"
    assert result.public.round == 4
    assert result.public.blind_score == 675
    assert result.public.hands_remaining == 7
    assert result.public.discards_remaining == 0
    assert len(result.public.hand) == 8
    assert len(result.draw_pile) == 44
    assert "nr2" in result.rng.nodes


def test_env_r2_nonboss_blind_start_leaves_inert_scoring_joker_untouched():
    run = _run()
    joker = FlatMultJoker(mult=11)
    run.public.jokers = [joker]

    result = prepare_supported_nonboss_blind_start(run)

    assert len(result.public.jokers) == 1
    assert isinstance(result.public.jokers[0], FlatMultJoker)
    assert result.public.jokers[0].mult == 11
    assert result.public.hands_remaining == 4
    assert result.public.discards_remaining == 3


def test_env_r2_nonboss_blind_start_fails_closed_on_unclassified_joker():
    run = _run()
    run.public.jokers = [_UnsupportedBlindStartJoker()]

    with pytest.raises(HeadlessTransitionError, match="unsupported identity"):
        prepare_supported_nonboss_blind_start(run)


def test_env_r2_nonboss_blind_start_rejects_tags_vouchers_and_boss_state():
    run = _run()
    run.tags.append("DOUBLE")
    with pytest.raises(HeadlessTransitionError, match="active tags"):
        prepare_supported_nonboss_blind_start(run)

    run = _run()
    run.public.vouchers.append("Grabber")
    with pytest.raises(HeadlessTransitionError, match="vouchers"):
        prepare_supported_nonboss_blind_start(run)

    run = _run()
    run.public.boss_name = "The Hook"
    with pytest.raises(HeadlessTransitionError, match="boss state"):
        prepare_supported_nonboss_blind_start(run)
