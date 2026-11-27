import pytest

from games.balatro.card import BalatroCard
from games.balatro.env.blind_progression import BlindProgressionState, finalize_won_round_progression
from games.balatro.env.episode_backend import pristine_red_white_reset
from games.balatro.env.observation_encoding import PUBLIC_OBSERVATION_SCHEMA, RANKS
from games.balatro.env.rng import BalatroRNG
from games.balatro.env.state import EnvStateFrame
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.mail_in_rebate import MailInRebateJoker


def test_env_r2_mail_initial_target_uses_permanent_creation_order_and_round_trips():
    run = pristine_red_white_reset("MAIL")
    rng = BalatroRNG("MAIL")
    index = rng.pseudorandom_element_index(52, "mail1")
    assert run.mail_rebate_rank == run.require_playing_card_order()[index].rank
    assert run.rng.nodes["mail1"] == rng.nodes["mail1"]

    payload = run.serialize()
    assert "mail_rebate_rank" not in payload["public"]
    assert HeadlessRunState.restore(payload).mail_rebate_rank == run.mail_rebate_rank
    payload["private"]["mail_rebate_rank"] = "Unknown"
    with pytest.raises(HeadlessTransitionError, match="invalid headless run-state snapshot"):
        HeadlessRunState.restore(payload)


@pytest.mark.parametrize(("blind", "ante"), [("Small", 1), ("Big", 1), ("Boss", 2)])
def test_env_r2_mail_resets_after_win_and_skips_stone_in_retained_order(blind, ante):
    run = pristine_red_white_reset("MAIL")
    eligible = [BalatroCard("2", "Clubs", debuffed=True), BalatroCard("K", "Clubs")]
    run.playing_card_order = [
        eligible[0], BalatroCard("4", "Clubs", enhancement="Stone"), eligible[1],
    ]
    run.public.owned_deck = list(reversed(run.playing_card_order))
    run.public.phase = "ROUND_EVAL"
    run.castle_suit = None
    joker = MailInRebateJoker(run.mail_rebate_rank)
    run.public.jokers = [joker]
    progression = BlindProgressionState(
        blind_on_deck=blind, **{f"{blind.lower()}_status": "Current"}
    )
    run.blind_progression_state = progression
    run.public.score = run.public.blind_score
    rng = BalatroRNG.from_snapshot(run.rng_snapshot())
    index = rng.pseudorandom_element_index(2, f"mail{ante}")

    result, _ = finalize_won_round_progression(run, progression, blind_type=blind)

    assert result.mail_rebate_rank == result.public.jokers[0].rank == eligible[index].rank
    assert result.rng_snapshot() == rng.snapshot()
    assert joker.rank == run.mail_rebate_rank


def test_env_r2_mail_existing_observation_slot_contains_the_owned_target():
    run = pristine_red_white_reset("MAIL")
    run.public.jokers = [MailInRebateJoker(run.mail_rebate_rank)]
    observation = EnvStateFrame(run.public).encoded_observation()
    index = PUBLIC_OBSERVATION_SCHEMA.feature_names.index("jokers.0.rank")
    assert observation.values[index] == RANKS.index(run.mail_rebate_rank) + 1
