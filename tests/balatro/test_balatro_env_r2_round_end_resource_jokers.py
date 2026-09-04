import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.deal import deal_pristine_round_start
from games.balatro.env.round_end import cash_out_baseline_ordinary_blind
from games.balatro.env.transition import HeadlessRunState
from games.balatro.jokers.drunkard import DrunkardJoker
from games.balatro.jokers.merry_andy import MerryAndyJoker
from games.balatro.jokers.stuntman import StuntmanJoker
from games.balatro.jokers.troubadour import TroubadourJoker
from games.balatro.state import BalatroState


def _cleared_run() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "DRAW_TO_HAND"
    state.money = 14
    state.blind = Blind(BlindType.SMALL, requirement=100, reward=3)

    run = deal_pristine_round_start(HeadlessRunState(public=state, seed="RESOURCE-CASHOUT"))
    run.public.phase = "ROUND_EVAL"
    run.public.score = 120
    run.public.hands_remaining = 2
    return run


@pytest.mark.parametrize(
    "joker_type",
    [StuntmanJoker, DrunkardJoker, TroubadourJoker, MerryAndyJoker],
)
def test_env_r2_resource_sensitive_acquisitions_are_inert_at_cashout(joker_type):
    run = _cleared_run()
    joker = joker_type()
    run.public.jokers.append(joker)

    result = cash_out_baseline_ordinary_blind(run)

    assert result.public.money == 21
    assert len(result.public.jokers) == 1
    assert type(result.public.jokers[0]) is joker_type
    # Cash-out must not replay acquisition/round-start capacity mutations.
    assert result.public.hand_size == run.public.hand_size
    assert result.public.round_reset_hands == run.public.round_reset_hands
    assert result.public.round_reset_discards == run.public.round_reset_discards
