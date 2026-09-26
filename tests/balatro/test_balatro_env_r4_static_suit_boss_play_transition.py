import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import start_supported_static_suit_debuff_boss
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.serialization import serialize_headless_run_state
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


STATIC_SUIT_BOSSES = (
    ("The Goad", "Spades"),
    ("The Window", "Diamonds"),
    ("The Head", "Hearts"),
    ("The Club", "Clubs"),
)


def _static_suit_run(boss_name: str, *, seed: str) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 2
    state.round = 5
    state.blind = Blind(BlindType.BOSS, requirement=99_999, reward=5)
    state.boss_name = boss_name
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return start_supported_static_suit_debuff_boss(
        HeadlessRunState(public=state, seed=seed)
    )


def _run_with_debuffed_hand_card(boss_name: str) -> HeadlessRunState:
    for index in range(20):
        run = _static_suit_run(boss_name, seed=f"R4-{boss_name}-{index}")
        if any(card.debuffed for card in run.public.hand):
            return run
    raise AssertionError(f"deterministic seeds did not deal a debuffed {boss_name} card")


@pytest.mark.parametrize(("boss_name", "suit"), STATIC_SUIT_BOSSES)
def test_env_r4_static_suit_boss_play_scores_base_without_debuffed_card_chips(
    boss_name,
    suit,
):
    run = _run_with_debuffed_hand_card(boss_name)
    selected_index = next(
        index for index, card in enumerate(run.public.hand) if card.debuffed
    )
    selected = run.public.hand[selected_index]
    before_rng = run.rng_snapshot()

    result = apply_supported_ordinary_play(run, (selected_index,))

    assert selected.suit == suit
    assert result.public.score == 5
    assert result.public.hands_remaining == 3
    assert result.public.phase == "SELECTING_HAND"
    assert result.public.discard_pile[-1].debuffed is True
    assert result.rng_snapshot() == before_rng
    assert sum(card.debuffed for card in result.require_playing_card_order()) == 13


def test_env_r4_static_suit_boss_clean_card_keeps_ordinary_rank_chips():
    run = _run_with_debuffed_hand_card("The Head")
    selected_index = next(
        index for index, card in enumerate(run.public.hand) if not card.debuffed
    )
    selected = run.public.hand[selected_index]

    result = apply_supported_ordinary_play(run, (selected_index,))

    assert result.public.score == 5 + BalatroScorer.RANK_CHIPS[selected.rank]


@pytest.mark.parametrize(("boss_name", "suit"), STATIC_SUIT_BOSSES)
def test_env_r4_static_suit_boss_play_rejects_inexact_debuff_state_atomically(
    boss_name,
    suit,
):
    run = _static_suit_run(boss_name, seed=f"R4-{boss_name}-BAD")
    wrong = next(card for card in run.require_playing_card_order() if card.suit != suit)
    wrong.debuffed = True
    before = serialize_headless_run_state(run)

    with pytest.raises(HeadlessTransitionError, match="incomplete or unowned"):
        apply_supported_ordinary_play(run, (0,))

    assert serialize_headless_run_state(run) == before
