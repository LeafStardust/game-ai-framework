import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_progression import BlindProgressionState
from games.balatro.env.boss_selection import BossSelectionState
from games.balatro.env.terminal_win import require_ante_8_win_boundary
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _win_boundary():
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "ROUND_EVAL"
    state.ante = 8
    state.blind = Blind(BlindType.BOSS, requirement=100_000, reward=8)
    state.boss_name = "Verdant Leaf"
    state.score = 100_000
    selection = BossSelectionState()
    selection.usage_counts["bl_final_leaf"] = 1
    return HeadlessRunState(
        public=state,
        seed="PPO-WIN",
        blind_progression_state=BlindProgressionState(
            small_status="Defeated",
            big_status="Defeated",
            boss_status="Current",
            blind_on_deck="Boss",
            blind_ante=8,
            boss_name="Verdant Leaf",
        ),
        boss_selection_state=selection,
    )


def test_env_ppo_terminal_win_accepts_exact_current_ante_8_showdown():
    require_ante_8_win_boundary(_win_boundary())


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda run: setattr(run.public, "ante", 7), "showdown boundary"),
        (lambda run: setattr(run.public, "score", 99_999), "target to be met"),
        (
            lambda run: setattr(run.public.blind, "requirement", -1),
            "target to be met",
        ),
        (
            lambda run: setattr(run.blind_progression_state, "boss_status", "Defeated"),
            "showdown boundary",
        ),
        (
            lambda run: setattr(run.blind_progression_state, "boss_name", "Amber Acorn"),
            "showdown boundary",
        ),
    ],
)
def test_env_ppo_terminal_win_rejects_inexact_boundaries(mutation, message):
    run = _win_boundary()
    mutation(run)

    with pytest.raises(HeadlessTransitionError, match=message):
        require_ante_8_win_boundary(run)
