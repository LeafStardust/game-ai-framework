import pytest

from games.balatro.card import BalatroCard
from games.balatro.env.blind_progression import (
    BlindProgressionState,
    finalize_won_round_progression,
)
from games.balatro.env.episode_backend import pristine_red_white_reset
from games.balatro.env.rng import BalatroRNG
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.castle import CastleJoker


def test_env_r2_initial_castle_target_draws_from_creation_order_and_round_trips():
    run = pristine_red_white_reset("CASTLE")
    expected_rng = BalatroRNG("CASTLE")
    index = expected_rng.pseudorandom_element_index(52, "cas1")

    assert run.castle_suit == run.require_playing_card_order()[index].suit
    assert run.rng.nodes["cas1"] == expected_rng.nodes["cas1"]
    payload = run.serialize()
    assert "castle_suit" not in payload["public"]
    assert HeadlessRunState.restore(payload).serialize() == payload
    payload["private"]["castle_suit"] = "Unknown"
    with pytest.raises(HeadlessTransitionError):
        HeadlessRunState.restore(payload)


@pytest.mark.parametrize(("blind_type", "key"), [("Small", "cas1"), ("Big", "cas1"), ("Boss", "cas2")])
def test_env_r2_castle_resets_on_wins_including_after_boss_ante_advance(blind_type, key):
    run = pristine_red_white_reset("CASTLE")
    eligible = [
        BalatroCard("2", "Diamonds", debuffed=True),
        BalatroCard("4", "Hearts", enhancement="Wild"),
    ]
    run.playing_card_order = [eligible[0], BalatroCard("3", "Clubs", enhancement="Stone"), eligible[1]]
    run.public.owned_deck = list(reversed(run.playing_card_order))
    run.public.deck = []
    run.public.phase = "ROUND_EVAL"
    run.public.score = run.public.blind_score
    run.castle_suit = "Spades"
    joker = CastleJoker("Spades")
    joker.chips = 21
    run.public.jokers = [joker]
    progression = BlindProgressionState(
        blind_on_deck=blind_type,
        **{f"{blind_type.lower()}_status": "Current"},
    )
    run.blind_progression_state = progression
    snapshot = run.rng_snapshot()
    expected_rng = BalatroRNG.from_snapshot(snapshot)
    index = expected_rng.pseudorandom_element_index(2, key)

    result, _ = finalize_won_round_progression(run, progression, blind_type=blind_type)

    assert result.rng.snapshot() == expected_rng.snapshot()
    assert result.castle_suit == result.public.jokers[0].suit == eligible[index].suit
    assert result.public.jokers[0].chips == 21
    assert run.castle_suit == joker.suit == "Spades"
    assert run.rng_snapshot() == snapshot


def test_env_r2_castle_all_stone_falls_back_without_a_draw():
    run = pristine_red_white_reset("CASTLE")
    for card in run.require_playing_card_order():
        card.enhancement = "Stone"
    run.public.phase = "ROUND_EVAL"
    run.public.score = run.public.blind_score
    progression = BlindProgressionState(small_status="Current")
    run.blind_progression_state = progression
    snapshot = run.rng_snapshot()

    result, _ = finalize_won_round_progression(run, progression, blind_type="Small")

    assert result.castle_suit == "Spades"
    assert result.rng_snapshot() == snapshot
