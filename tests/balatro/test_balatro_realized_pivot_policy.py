from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.hologram import HologramJoker
from games.balatro.jokers.runner import RunnerJoker
from games.balatro.realized_pivot_policy import pivot_readiness
from games.balatro.state import BalatroState


def _state(*, ante, money=0):
    state = BalatroState()
    state.ante = ante
    state.money = money
    return state


def test_late_runner_without_straight_history_has_low_realized_pivot_readiness():
    state = _state(ante=6)
    state.hand_play_counts["STRAIGHT"] = 0

    result = pivot_readiness(state, RunnerJoker())

    assert result.readiness < 0.5
    assert result.buildup_cost > 0.5


def test_runner_with_existing_straight_history_can_be_ready_now():
    state = _state(ante=6)
    state.hand_play_counts["STRAIGHT"] = 8

    result = pivot_readiness(state, RunnerJoker())

    assert result.readiness == 1.0
    assert result.buildup_cost == 0.0


def test_hologram_late_without_generator_pays_buildup_cost():
    state = _state(ante=5)

    result = pivot_readiness(state, HologramJoker())

    assert result.readiness < 0.5


def test_cash_scorer_with_large_existing_bankroll_is_immediately_ready():
    state = _state(ante=6, money=60)

    result = pivot_readiness(state, BullJoker())

    assert result.readiness == 1.0
    assert result.buildup_cost == 0.0
