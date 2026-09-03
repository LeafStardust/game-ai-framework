import pytest

from games.balatro.blinds.blind import create_big_blind, create_small_blind
from games.balatro.env.blind_start import prepare_supported_nonboss_blind_start
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.burglar import BurglarJoker
from games.balatro.jokers.juggler import JugglerJoker
from games.balatro.jokers.turtle_bean import TurtleBeanJoker
from games.balatro.state import BalatroState


def _run(*, big=False, round_num=4, bonus_hands=0, bonus_discards=0):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 2
    state.round = round_num
    state.blind = create_big_blind(2400) if big else create_small_blind(1200)
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    state.score = 777
    state.hands_remaining = 1
    state.discards_remaining = 1
    state.discards_used = 2
    state.last_played_hand = "PAIR"
    state.round_hand_play_counts["PAIR"] = 3
    return HeadlessRunState(
        public=state,
        seed="NONBOSS",
        round_bonus_hands=bonus_hands,
        round_bonus_discards=bonus_discards,
    )


@pytest.mark.parametrize("big", [False, True])
def test_env_r2_nonboss_start_composes_round_bonus_burglar_and_consumption(big):
    run = _run(big=big, bonus_hands=2, bonus_discards=1)
    run.public.jokers = [JugglerJoker(), BurglarJoker()]

    result = prepare_supported_nonboss_blind_start(run)

    assert result is not run
    assert run.public.round == 4
    assert run.public.score == 777
    assert result.public.round == 5
    assert result.public.phase == "DRAW_TO_HAND"
    assert result.public.blind_score == (2400 if big else 1200)
    assert result.public.score == 0
    assert result.public.hands_remaining == 9  # 4 reset + 2 bonus + 3 Burglar
    assert result.public.discards_remaining == 0
    assert result.public.discards_used == 0
    assert result.public.last_played_hand is None
    assert all(value == 0 for value in result.public.round_hand_play_counts.values())
    assert result.round_bonus_hands == 0
    assert result.round_bonus_discards == 0
    assert result.rng_snapshot() == run.rng_snapshot()


def test_env_r2_nonboss_start_rejects_unclassified_joker_before_mutating_source():
    run = _run()
    run.public.jokers = [TurtleBeanJoker()]

    with pytest.raises(HeadlessTransitionError, match="unsupported identity"):
        prepare_supported_nonboss_blind_start(run)

    assert run.public.round == 4
    assert run.public.phase == "BLIND_SELECT"
    assert run.round_bonus_hands == 0


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda run: run.tags.append("DOUBLE"), "active tags"),
        (lambda run: run.public.vouchers.append("GRABBER"), "vouchers"),
        (lambda run: setattr(run.public, "phase", "SHOP"), "BLIND_SELECT"),
        (lambda run: setattr(run.public, "blind", None), "Small or Big Blind"),
        (lambda run: setattr(run.public, "round", True), "round must be"),
    ],
)
def test_env_r2_nonboss_start_fails_closed_on_unowned_boundary(mutate, message):
    run = _run()
    mutate(run)

    with pytest.raises(HeadlessTransitionError, match=message):
        prepare_supported_nonboss_blind_start(run)


def test_env_r2_nonboss_start_requires_empty_transition_card_zones():
    run = _run()
    run.public.hand = [run.public.deck[0]]

    with pytest.raises(HeadlessTransitionError, match="empty transition card zones"):
        prepare_supported_nonboss_blind_start(run)
